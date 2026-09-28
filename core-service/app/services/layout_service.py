"""Layout service for managing warehouse location hierarchy (Zone → Aisle → Bay → Level → Bin)"""

import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.bin_stock_level import BinStockLevel
from app.models.warehouse import Warehouse
from app.models.warehouse_location import LocationType, WarehouseLocation
from app.services.capacity_math import (
    CC_PER_M3,
    G_PER_KG,
    effective_bin_count_capacity,
    effective_bin_volume_limit_cc,
    effective_bin_weight_limit_g,
)

# Valid parent type mapping: child_type -> expected parent location_type
# "zone" parent is the warehouse itself (parent_location_id is None)
VALID_PARENT_TYPES: dict[str, str] = {
    "zone": "warehouse",
    "aisle": "zone",
    "bay": "aisle",
    "level": "bay",
    "bin": "level",
}

# Sentinel distinguishing "field omitted" from "field set to null" on PATCH,
# so callers can explicitly clear a volume/weight limit.
_UNSET = object()


class LayoutService:
    """Service for managing the warehouse location hierarchy."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create_location(
        self,
        warehouse_id: UUID,
        organization_id: UUID,
        location_type: str,
        code: str,
        name: str | None = None,
        parent_location_id: UUID | None = None,
        capacity: Decimal | None = None,
        capacity_uom: str | None = None,
        position_x: Decimal | None = None,
        position_y: Decimal | None = None,
        max_volume_cc: Decimal | None = None,
        max_weight_grams: Decimal | None = None,
    ) -> WarehouseLocation:
        """
        Create a new location node in the warehouse hierarchy.

        Validates the parent-child hierarchy and generates the full_path code.

        Args:
            warehouse_id: The warehouse this location belongs to.
            organization_id: The organization owning the warehouse.
            location_type: One of zone, aisle, bay, level, bin.
            code: Short code for this location (e.g., Z01, A03).
            name: Optional human-readable name.
            parent_location_id: Parent location UUID (None for zones).
            capacity: Storage capacity of this location.
            capacity_uom: Unit of measure for capacity.
            position_x: X coordinate for routing.
            position_y: Y coordinate for routing.
            max_volume_cc: Max volume capacity in cubic centimetres (cc).
            max_weight_grams: Max weight capacity in grams.

        Returns:
            The created WarehouseLocation.

        Raises:
            ValidationError: If hierarchy rules are violated.
        """
        # Validate location_type
        if location_type not in VALID_PARENT_TYPES:
            raise ValidationError(
                f"Invalid location_type '{location_type}'. "
                f"Must be one of: {', '.join(VALID_PARENT_TYPES.keys())}"
            )

        # Validate hierarchy
        self._validate_hierarchy(location_type, parent_location_id, organization_id)

        # Build clean raw code for DB storage (e.g. zone + "01" → "Z01")
        # Display formatting (e.g. "Z-01") is done on-the-fly in get_tree()
        raw_code = self._build_raw_code(location_type, code)

        # Generate full_path using the clean raw code (no dashes inside codes)
        full_path = self._generate_location_code(parent_location_id, raw_code)

        # Check for duplicate full_path within the same warehouse
        existing = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.full_path == full_path,
            )
            .first()
        )
        if existing:
            raise ValidationError(
                f"A location with path '{full_path}' already exists in this warehouse"
            )

        location = WarehouseLocation(
            warehouse_id=warehouse_id,
            organization_id=organization_id,
            location_type=location_type,
            code=raw_code,
            full_path=full_path,
            name=name,
            parent_location_id=parent_location_id,
            capacity=capacity or Decimal("0"),
            total_capacity=capacity or Decimal("0"),
            available_capacity=capacity or Decimal("0"),
            capacity_uom=capacity_uom,
            position_x=position_x or Decimal("0"),
            position_y=position_y or Decimal("0"),
            max_volume_cc=max_volume_cc,
            max_weight_grams=max_weight_grams,
            is_active=True,
        )

        # Auto-generate unique 5-char QR code for bins
        if location_type == "bin":
            location.qr_code = self._generate_qr_code()

        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)
        return location

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update_location(
        self,
        location_id: UUID,
        organization_id: UUID,
        name: str | None = None,
        capacity: Decimal | None = None,
        capacity_uom: str | None = None,
        position_x: Decimal | None = None,
        position_y: Decimal | None = None,
        max_volume_cc: Decimal | None | object = _UNSET,
        max_weight_grams: Decimal | None | object = _UNSET,
    ) -> WarehouseLocation:
        """
        Update a location's mutable fields (name, capacity, position).

        Does NOT allow changing location_type, parent, or code after creation.

        Args:
            location_id: The location to update.
            organization_id: Organization scope.
            name: New name (optional).
            capacity: New capacity (optional).
            capacity_uom: New capacity UOM (optional).
            position_x: New X position (optional).
            position_y: New Y position (optional).
            max_volume_cc: New max volume capacity in cc (optional).
            max_weight_grams: New max weight capacity in grams (optional).

        Returns:
            The updated WarehouseLocation.

        Raises:
            ValidationError: If location not found.
        """
        location = self._get_location(location_id, organization_id)

        if name is not None:
            location.name = name
        if capacity is not None:
            location.capacity = capacity
            # For leaf nodes (bins), total_capacity equals capacity
            if location.location_type == LocationType.BIN.value:
                location.total_capacity = capacity
        if capacity_uom is not None:
            location.capacity_uom = capacity_uom
        if position_x is not None:
            location.position_x = position_x
        if position_y is not None:
            location.position_y = position_y
        if max_volume_cc is not _UNSET:
            location.max_volume_cc = max_volume_cc
        if max_weight_grams is not _UNSET:
            location.max_weight_grams = max_weight_grams

        location.version += 1
        self.db.commit()
        self.db.refresh(location)

        # Changing a bin's volume/weight limit should immediately re-evaluate
        # its capacity state (pct, bin_state, is_available) for the dashboard.
        if location.location_type == LocationType.BIN.value and (
            max_volume_cc is not _UNSET or max_weight_grams is not _UNSET
        ):
            from app.services.bin_capacity_service import BinCapacityService

            BinCapacityService(self.db).refresh_bin(location.id, organization_id)
            self.db.commit()

        return location

    # ------------------------------------------------------------------
    # DEACTIVATE (cascade to descendants)
    # ------------------------------------------------------------------

    def deactivate_location(
        self,
        location_id: UUID,
        organization_id: UUID,
    ) -> WarehouseLocation:
        """
        Deactivate a location and all its descendants.

        Deactivated locations cannot receive new stock.

        Args:
            location_id: The location to deactivate.
            organization_id: Organization scope.

        Returns:
            The deactivated WarehouseLocation (root of cascade).

        Raises:
            ValidationError: If location not found.
        """
        location = self._get_location(location_id, organization_id)

        # Deactivate the location itself
        location.is_active = False
        location.version += 1

        # Cascade deactivation to all descendants
        descendants = self._get_all_descendants(location_id)
        for descendant in descendants:
            descendant.is_active = False
            descendant.version += 1

        self.db.commit()
        self.db.refresh(location)
        return location

    # ------------------------------------------------------------------
    # GET TREE
    # ------------------------------------------------------------------

    def get_tree(
        self,
        warehouse_id: UUID,
        organization_id: UUID,
    ) -> list[dict[str, Any]]:
        """
        Return the full location hierarchy for a warehouse as a nested tree.

        Args:
            warehouse_id: The warehouse to get the tree for.
            organization_id: Organization scope.

        Returns:
            A list of root-level location dicts, each with a 'children' key.
        """
        # Fetch all active locations for this warehouse
        locations = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == organization_id,
                WarehouseLocation.is_active.is_(True),
            )
            .order_by(WarehouseLocation.full_path)
            .all()
        )

        # Build tree structure
        location_map: dict[UUID, dict] = {}
        roots: list[dict] = []

        # Live volume/weight rollup keyed by location id (one implementation, in
        # BinCapacityService). Ancestors carry no limit columns of their own, so
        # without this they reported the legacy unit-count zeros — and their
        # cached `available_capacity` is `0 - used_eaches`, which is how a zone
        # ends up reporting a *negative* available capacity.
        rollup: dict[str, dict] = {}
        if locations:
            from app.services.bin_capacity_service import BinCapacityService

            for entry in self._iter_capacity_nodes(
                BinCapacityService(self.db).get_capacity_tree(
                    warehouse_id, organization_id
                )
            ):
                rollup[str(entry["node"])] = entry

        # The warehouse decides which dimensions capacity tracking uses at all;
        # the fallback below must honour the same switches as the rollup, or a
        # bin reports a physical limit the rest of the system ignores.
        warehouse = (
            self.db.query(Warehouse)
            .filter(
                Warehouse.id == warehouse_id,
                Warehouse.organization_id == organization_id,
            )
            .first()
        )
        use_volume = getattr(warehouse, "use_volume", None) is not False
        use_weight = getattr(warehouse, "use_weight", None) is True

        for loc in locations:
            # Build raw code (Z01, A01, B01, L01, BN001) — no dashes
            individual_code = self._build_raw_code(loc.location_type, loc.code or "")
            capacity, total_capacity, available, capacity_uom = self._reported_capacity(
                loc,
                rollup.get(str(loc.id)),
                use_volume=use_volume,
                use_weight=use_weight,
            )
            node = {
                "id": loc.id,
                "warehouse_id": loc.warehouse_id,
                "location_type": loc.location_type,
                "code": individual_code,
                "full_path": "",  # computed below from parent chain
                "name": loc.name,
                "capacity": capacity,
                "total_capacity": total_capacity,
                "available_capacity": available,
                "capacity_uom": capacity_uom,
                "position_x": loc.position_x,
                "position_y": loc.position_y,
                "max_volume_cc": loc.max_volume_cc,
                "max_weight_grams": loc.max_weight_grams,
                "is_active": loc.is_active,
                "is_pickable": loc.is_pickable,
                "qr_code": loc.qr_code,
                "parent_location_id": loc.parent_location_id,
                "children": [],
            }
            location_map[loc.id] = node

        for loc in locations:
            node = location_map[loc.id]
            if loc.parent_location_id and loc.parent_location_id in location_map:
                parent = location_map[loc.parent_location_id]
                # Build full_path from parent chain using raw codes
                node["full_path"] = parent["full_path"] + "-" + node["code"]
                parent["children"].append(node)
            else:
                # Root node (zone) — full_path is just its own code
                node["full_path"] = node["code"]
                roots.append(node)

        return roots

    @staticmethod
    def _iter_capacity_nodes(node: dict[str, Any]):
        """Yield a capacity-tree node and all of its descendants."""
        yield node
        for child in node.get("children", []):
            yield from LayoutService._iter_capacity_nodes(child)

    @staticmethod
    def _binding_capacity(
        entry: dict[str, Any],
    ) -> tuple[Decimal, Decimal, Decimal, str] | None:
        """Binding dimension of a rollup entry as ``(capacity, total, available, uom)``.

        ``BinCapacityService`` derives bin state from the *binding* dimension
        (``binding_pct = max(vol_pct, wt_pct)``), so the reported capacity has to
        use the same one. Always exposing volume made a bin whose weight is at
        95% look nearly empty. ``None`` when the entry limits neither dimension.
        """
        candidates: list[tuple[Decimal, tuple[Decimal, Decimal, Decimal, str]]] = []

        volume = entry["volume"]
        if volume["capacity_m3"] is not None:
            candidates.append(
                (
                    volume["pct"] or Decimal("0"),
                    (
                        volume["capacity_m3"],
                        volume["capacity_m3"],
                        volume["capacity_m3"] - volume["occupied_m3"],
                        "volume",
                    ),
                )
            )

        weight = entry["weight"]
        if weight["capacity_kg"] is not None:
            candidates.append(
                (
                    weight["pct"] or Decimal("0"),
                    (
                        weight["capacity_kg"],
                        weight["capacity_kg"],
                        weight["capacity_kg"] - weight["occupied_kg"],
                        "weight",
                    ),
                )
            )

        if not candidates:
            return None
        return max(candidates, key=lambda item: item[0])[1]

    @staticmethod
    def _reported_capacity(
        loc: WarehouseLocation,
        rollup_entry: dict[str, Any] | None = None,
        *,
        use_volume: bool = True,
        use_weight: bool = False,
    ) -> tuple[Decimal, Decimal, Decimal, str | None]:
        """Capacity of a location in its own measure.

        Returns ``(capacity, total_capacity, available_capacity, capacity_uom)``.

        A layout bin carries its physical limit in ``max_volume_cc`` /
        ``max_weight_grams`` with ``capacity_uom='volume'``, and deliberately
        leaves the legacy unit-count ``capacity`` / ``total_capacity`` columns at
        0 so ``CapacityService`` is unaffected. Returning those raw made every
        layout bin report ``capacity: 0`` while ``available_capacity`` was a real
        cubic-metre figure.

        The live rollup wins when it limits a dimension (the *binding* one, so
        the number matches ``bin_state``); otherwise the rollup's aggregated
        ``count_capacity`` covers count-limited bins and their ancestors; only
        then are the location's own limits considered, gated on the warehouse's
        ``use_volume`` / ``use_weight`` switches so the tree cannot advertise a
        dimension the rest of the system ignores.
        """
        if rollup_entry is not None:
            binding = LayoutService._binding_capacity(rollup_entry)
            if binding is not None:
                return binding

            # Count-limited layout: the bin's own limit is aggregated onto every
            # ancestor, so read the rollup rather than the ancestor's 0 column.
            rollup_count = rollup_entry["count_capacity"]
            if rollup_count is not None:
                units = rollup_entry["unit_count"]
                return (
                    rollup_count,
                    rollup_count,
                    rollup_count - units,
                    loc.capacity_uom,
                )

        count_cap = effective_bin_count_capacity(loc)
        if count_cap is not None:
            return (
                count_cap,
                loc.total_capacity,
                loc.available_capacity,
                loc.capacity_uom,
            )

        if use_volume:
            volume_cc = effective_bin_volume_limit_cc(loc)
            if volume_cc is not None:
                capacity_m3 = volume_cc / CC_PER_M3
                return capacity_m3, capacity_m3, loc.available_capacity, "volume"

        if use_weight:
            weight_g = effective_bin_weight_limit_g(loc)
            if weight_g is not None:
                capacity_kg = weight_g / G_PER_KG
                return capacity_kg, capacity_kg, loc.available_capacity, "weight"

        stored_uom = (loc.capacity_uom or "").strip().lower()
        if (stored_uom == "volume" and not use_volume) or (
            stored_uom == "weight" and not use_weight
        ):
            # The measure this location was configured in is not tracked by the
            # warehouse, so its stored capacity/available numbers must not be
            # advertised as usable capacity.
            return Decimal("0"), Decimal("0"), Decimal("0"), None

        return (
            loc.capacity,
            loc.total_capacity,
            loc.available_capacity,
            loc.capacity_uom,
        )

    # ------------------------------------------------------------------
    # LIST LOCATIONS (with filters and pagination)
    # ------------------------------------------------------------------

    def list_locations(
        self,
        warehouse_id: UUID,
        organization_id: UUID,
        location_type: str | None = None,
        parent_location_id: UUID | None = None,
        is_active: bool | None = None,
        has_stock: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """
        List locations with optional filters and pagination.

        Args:
            warehouse_id: Warehouse scope.
            organization_id: Organization scope.
            location_type: Filter by type (zone, aisle, bay, level, bin).
            parent_location_id: Filter by parent.
            is_active: Filter by active status.
            has_stock: Filter to only locations with stock > 0.
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Dict with 'locations' list and 'pagination' metadata.
        """
        query = self.db.query(WarehouseLocation).filter(
            WarehouseLocation.warehouse_id == warehouse_id,
            WarehouseLocation.organization_id == organization_id,
        )

        if location_type is not None:
            query = query.filter(WarehouseLocation.location_type == location_type)

        if parent_location_id is not None:
            query = query.filter(
                WarehouseLocation.parent_location_id == parent_location_id
            )

        if is_active is not None:
            query = query.filter(WarehouseLocation.is_active == is_active)

        if has_stock is True:
            # Only locations that have at least one bin_stock_level with qty > 0
            # For non-bin locations, check if any descendant bin has stock
            bin_ids_with_stock = (
                self.db.query(BinStockLevel.bin_location_id)
                .filter(BinStockLevel.quantity_on_hand > 0)
                .distinct()
                .subquery()
            )
            query = query.filter(
                or_(
                    # Direct bin with stock
                    WarehouseLocation.id.in_(bin_ids_with_stock),
                    # Parent locations that have descendant bins with stock
                    # We use full_path prefix matching for ancestor detection
                    WarehouseLocation.id.in_(
                        self.db.query(WarehouseLocation.parent_location_id)
                        .filter(
                            WarehouseLocation.id.in_(bin_ids_with_stock),
                            WarehouseLocation.parent_location_id.isnot(None),
                        )
                        .distinct()
                    ),
                )
            )

        # Count total before pagination
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        locations = (
            query.order_by(WarehouseLocation.full_path)
            .offset(offset)
            .limit(page_size)
            .all()
        )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "locations": locations,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }

    # ------------------------------------------------------------------
    # GET LOCATION SUMMARY (subtree stats)
    # ------------------------------------------------------------------

    def get_location_summary(
        self,
        location_id: UUID,
        organization_id: UUID,
    ) -> dict[str, Any]:
        """
        Get summary statistics for a location's subtree.

        Returns total bins, occupied bins, total/used/available capacity,
        and distinct item count within the subtree.

        Args:
            location_id: The location to summarize.
            organization_id: Organization scope.

        Returns:
            Dict with summary statistics.

        Raises:
            ValidationError: If location not found.
        """
        location = self._get_location(location_id, organization_id)

        # All descendant location IDs (including self), regardless of state.
        descendant_ids = [location.id] + [
            d.id for d in self._get_all_descendants(location_id)
        ]

        # Active bins in the subtree — the single source of truth used for
        # BOTH total capacity and used capacity. This prevents an inactive
        # bin's leftover stock from producing phantom utilization (the count
        # dashboard and the volume Location Tree would otherwise disagree).
        active_bin_ids = [
            row[0]
            for row in self.db.query(WarehouseLocation.id)
            .filter(
                WarehouseLocation.id.in_(descendant_ids),
                WarehouseLocation.location_type == LocationType.BIN.value,
                WarehouseLocation.is_active.is_(True),
            )
            .all()
        ]

        # Count bins in subtree (active only, matching the capacity rollups)
        total_bins = len(active_bin_ids)

        # Count occupied bins (active bins with stock > 0)
        if active_bin_ids:
            occupied_bins = (
                self.db.query(func.count(func.distinct(BinStockLevel.bin_location_id)))
                .filter(
                    BinStockLevel.bin_location_id.in_(active_bin_ids),
                    BinStockLevel.quantity_on_hand > 0,
                )
                .scalar()
                or 0
            )
        else:
            occupied_bins = 0

        # Capacity in the location's own measure, from the same rollup the tree
        # reports. Layout bins carry their physical limit in `max_volume_cc` with
        # `capacity_uom='volume'` and leave the legacy unit-count `capacity`
        # columns at 0, so summing `WarehouseLocation.capacity` against stock
        # *units* reported zero total capacity and a negative available capacity
        # on a volume warehouse.
        measure = self._subtree_capacity(location)
        if measure is not None:
            total_capacity, used_capacity, available_capacity, capacity_uom = measure
        else:
            total_capacity = used_capacity = available_capacity = Decimal("0")
            capacity_uom = location.capacity_uom

        # Distinct items in active bins
        if active_bin_ids:
            distinct_items = (
                self.db.query(func.count(func.distinct(BinStockLevel.item_id)))
                .filter(
                    BinStockLevel.bin_location_id.in_(active_bin_ids),
                    BinStockLevel.quantity_on_hand > 0,
                )
                .scalar()
                or 0
            )
        else:
            distinct_items = 0

        return {
            "location_id": location.id,
            "location_type": location.location_type,
            "code": location.code,
            "full_path": location.full_path,
            "name": location.name,
            "is_active": location.is_active,
            "total_bins": total_bins,
            "occupied_bins": occupied_bins,
            "total_capacity": total_capacity,
            "used_capacity": used_capacity,
            "available_capacity": available_capacity,
            "capacity_uom": capacity_uom,
            "distinct_items": distinct_items,
        }

    def _subtree_capacity(
        self, location: WarehouseLocation
    ) -> tuple[Decimal, Decimal, Decimal, str | None] | None:
        """Capacity/used/available for a location's subtree, in its own measure.

        Reuses ``BinCapacityService.get_capacity_tree`` — the same rollup the
        location tree reports — so the summary and the tree cannot disagree.
        Returns ``None`` when the location is absent from the rollup (for example
        a deactivated location, which it filters out).
        """
        from app.services.bin_capacity_service import BinCapacityService

        tree = BinCapacityService(self.db).get_capacity_tree(
            location.warehouse_id, location.organization_id
        )
        entry = next(
            (
                node
                for node in self._iter_capacity_nodes(tree)
                if str(node["node"]) == str(location.id)
            ),
            None,
        )
        if entry is None:
            return None

        binding = self._binding_capacity(entry)
        if binding is not None:
            capacity, _total, available, uom = binding
            return capacity, capacity - available, available, uom

        count_cap = entry["count_capacity"]
        if count_cap is not None:
            units = entry["unit_count"]
            return count_cap, units, count_cap - units, location.capacity_uom

        return None

    # ------------------------------------------------------------------
    # SEARCH LOCATIONS
    # ------------------------------------------------------------------

    def search_locations(
        self,
        warehouse_id: UUID,
        organization_id: UUID,
        query: str,
        limit: int = 20,
    ) -> list[WarehouseLocation]:
        """
        Search locations by code or name (case-insensitive partial match).

        Args:
            warehouse_id: Warehouse scope.
            organization_id: Organization scope.
            query: Search string to match against code, full_path, or name.
            limit: Maximum results to return.

        Returns:
            List of matching WarehouseLocation objects.
        """
        search_pattern = f"%{query}%"

        results = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == organization_id,
                or_(
                    WarehouseLocation.code.ilike(search_pattern),
                    WarehouseLocation.full_path.ilike(search_pattern),
                    WarehouseLocation.name.ilike(search_pattern),
                ),
            )
            .order_by(WarehouseLocation.full_path)
            .limit(limit)
            .all()
        )

        return results

    # ------------------------------------------------------------------
    # GENERATE LOCATION CODE
    # ------------------------------------------------------------------

    def generate_location_code(
        self,
        parent_location_id: UUID | None,
        code: str,
    ) -> str:
        """
        Generate the full_path by concatenating ancestor codes with '-' separator.

        Public method for external use (e.g., by CapacityService).

        Args:
            parent_location_id: The parent location's ID (None for zones).
            code: The short code for this location.

        Returns:
            The full path string (e.g., 'Z01-A03-B02-L04-B01').
        """
        return self._generate_location_code(parent_location_id, code)

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _validate_hierarchy(
        self,
        location_type: str,
        parent_location_id: UUID | None,
        organization_id: UUID,
    ) -> None:
        """Validate that the parent-child hierarchy is correct."""
        expected_parent_type = VALID_PARENT_TYPES[location_type]

        if expected_parent_type == "warehouse":
            # Zones must NOT have a parent_location_id (they sit directly under the warehouse)
            if parent_location_id is not None:
                raise ValidationError(
                    "A zone must not have a parent_location_id. "
                    "Zones are top-level locations within a warehouse."
                )
        else:
            # All other types MUST have a parent_location_id
            if parent_location_id is None:
                raise ValidationError(
                    f"A {location_type} must have a parent location of type "
                    f"'{expected_parent_type}'."
                )

            # Validate the parent exists and is the correct type
            parent = (
                self.db.query(WarehouseLocation)
                .filter(
                    WarehouseLocation.id == parent_location_id,
                    WarehouseLocation.organization_id == organization_id,
                )
                .first()
            )

            if parent is None:
                raise ValidationError(
                    f"Parent location with ID '{parent_location_id}' not found."
                )

            if parent.location_type != expected_parent_type:
                raise ValidationError(
                    f"A {location_type} must have a {expected_parent_type} as parent, "
                    f"but the specified parent is of type '{parent.location_type}'."
                )

            # Ensure parent is active
            if not parent.is_active:
                raise ValidationError(
                    f"Cannot create a location under deactivated parent "
                    f"'{parent.full_path}'."
                )

    # Map location_type to its code prefix letter
    TYPE_CODE_PREFIX: dict[str, str] = {
        "zone": "Z",
        "aisle": "A",
        "bay": "B",
        "level": "L",
        "bin": "BN",
    }

    @staticmethod
    def _format_individual_code(code: str) -> str:
        """
        Insert a dash between letters and digits for readability.

        Examples:
            B01   → B-01
            L01   → L-01
            A01   → A-01
            Z01   → Z-01
            001   → 001   (no letters, unchanged)
            Z-01  → Z-01  (already formatted)
        """
        if not code:
            return code
        return re.sub(r"([A-Za-z]+)(\d+)", r"\1\2", code)

    @classmethod
    def _extract_trailing_number(cls, raw_code: str) -> str:
        """Extract the trailing digit sequence from any code format."""
        if not raw_code:
            return ""
        m = re.search(r"(\d+)$", raw_code)
        return m.group(1) if m else ""

    @classmethod
    def _build_individual_code(cls, location_type: str, raw_code: str) -> str:
        """
        Build a consistent dashed display code: {type-prefix}-{trailing-number}.

        Extracts the trailing digits from raw_code, so it handles:
          - Clean codes:            "01", "B01"
          - Full-path codes (legacy): "Z01-A01-B01", "z-01-A-01-B01"

        Examples:
            zone  + "01"            → Z-01
            aisle + "01"            → A-01
            bay   + "Z01-A01-B01"   → B-01
            level + "L01"           → L-01
            bin   + "z-01-A-01-001" → BN-001
        """
        prefix = cls.TYPE_CODE_PREFIX.get(location_type, "")
        numeric = cls._extract_trailing_number(raw_code)
        if not numeric:
            return raw_code
        return f"{prefix}{numeric}"

    @classmethod
    def _build_raw_code(cls, location_type: str, code: str) -> str:
        """
        Build a clean raw code for DB storage (no dashes inside the code).

        Examples:
            zone  + "01"  → Z01
            aisle + "01"  → A01
            bay   + "B01" → B01
            level + "L01" → L01
            bin   + "001" → BN001
        """
        prefix = cls.TYPE_CODE_PREFIX.get(location_type, "")
        numeric = cls._extract_trailing_number(code)
        if not numeric:
            return code
        return f"{prefix}{numeric}"

    def _generate_qr_code(self) -> str:
        """
        Generate a unique 5-character alphanumeric QR code for a bin.

        Excludes I, O, 0, 1 for readability.
        Retries on collision (extremely unlikely with 60M+ combinations).
        """
        import random

        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        for _ in range(10):  # safety limit
            code = "".join(random.choices(chars, k=5))
            exists = (
                self.db.query(WarehouseLocation)
                .filter(WarehouseLocation.qr_code == code)
                .first()
            )
            if not exists:
                return code
        raise RuntimeError("Failed to generate unique QR code after 10 attempts")

    @classmethod
    def _format_full_path(cls, full_path: str | None) -> str:
        """
        Format a DB full_path for display by inserting a dash only into the
        last segment (e.g. Z01-A01-B01-L01-BN001 → Z01-A01-B01-L01-BN-001).
        """
        if not full_path:
            return ""
        segments = full_path.split("-")
        if segments:
            segments[-1] = cls._format_individual_code(segments[-1])
        return "-".join(segments)

    def _generate_location_code(
        self,
        parent_location_id: UUID | None,
        code: str,
    ) -> str:
        """
        Generate full_path by concatenating ancestor codes with '-' separator.

        For zones (no parent), the full_path is just the code itself.
        For deeper levels, it's parent.full_path + '-' + code.

        Codes are stored raw (e.g. "01") — display formatting is applied
        separately in get_tree().
        """
        if parent_location_id is None:
            return code

        parent = (
            self.db.query(WarehouseLocation)
            .filter(WarehouseLocation.id == parent_location_id)
            .first()
        )

        if parent is None:
            return code

        return f"{parent.full_path}-{code}"

    def _get_location(
        self,
        location_id: UUID,
        organization_id: UUID,
    ) -> WarehouseLocation:
        """Get a location by ID, raising ValidationError if not found."""
        location = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id == location_id,
                WarehouseLocation.organization_id == organization_id,
            )
            .first()
        )

        if location is None:
            raise ValidationError(f"Location with ID '{location_id}' not found.")

        return location

    def get_location_qr_payload(
        self,
        location_id: UUID,
        organization_id: UUID,
    ) -> "LocationQRPayload":
        """Build QR payload with warehouse and location context.

        Returns a payload suitable for encoding into a bin location QR code.
        The mobile app decodes this JSON to identify the exact bin.
        """
        from app.schemas.warehouse_location import LocationQRPayload

        location = self._get_location(location_id, organization_id)
        warehouse = (
            self.db.query(Warehouse)
            .filter(Warehouse.id == location.warehouse_id)
            .first()
        )

        return LocationQRPayload(
            org_id=organization_id,
            warehouse_id=location.warehouse_id,
            warehouse_code=warehouse.code if warehouse else "",
            warehouse_name=warehouse.name if warehouse else "",
            location_id=location.id,
            full_path=location.full_path or "",
            location_type=location.location_type,
            location_code=location.code,
            qr_code=location.qr_code,
            bin_code=location.qr_code,
        )

    def _get_all_descendants(
        self,
        location_id: UUID,
    ) -> list[WarehouseLocation]:
        """
        Get all descendants of a location (recursive).

        Uses iterative BFS to avoid deep recursion issues.
        """
        descendants: list[WarehouseLocation] = []
        queue = [location_id]

        while queue:
            current_id = queue.pop(0)
            children = (
                self.db.query(WarehouseLocation)
                .filter(WarehouseLocation.parent_location_id == current_id)
                .all()
            )
            for child in children:
                descendants.append(child)
                queue.append(child.id)

        return descendants
