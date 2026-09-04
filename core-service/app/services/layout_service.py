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

# Valid parent type mapping: child_type -> expected parent location_type
# "zone" parent is the warehouse itself (parent_location_id is None)
VALID_PARENT_TYPES: dict[str, str] = {
    "zone": "warehouse",
    "aisle": "zone",
    "bay": "aisle",
    "level": "bay",
    "bin": "level",
}


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

        location.version += 1
        self.db.commit()
        self.db.refresh(location)
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

        for loc in locations:
            # Build raw code (Z01, A01, B01, L01, BN001) — no dashes
            individual_code = self._build_raw_code(loc.location_type, loc.code or "")
            node = {
                "id": loc.id,
                "warehouse_id": loc.warehouse_id,
                "location_type": loc.location_type,
                "code": individual_code,
                "full_path": "",  # computed below from parent chain
                "name": loc.name,
                "capacity": loc.capacity,
                "total_capacity": loc.total_capacity,
                "available_capacity": loc.available_capacity,
                "capacity_uom": loc.capacity_uom,
                "position_x": loc.position_x,
                "position_y": loc.position_y,
                "is_active": loc.is_active,
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

        # Get all descendant bins (including self if it's a bin)
        descendant_ids = [location.id] + [
            d.id for d in self._get_all_descendants(location_id)
        ]

        # Count bins in subtree
        total_bins = (
            self.db.query(func.count(WarehouseLocation.id))
            .filter(
                WarehouseLocation.id.in_(descendant_ids),
                WarehouseLocation.location_type == LocationType.BIN.value,
            )
            .scalar()
            or 0
        )

        # Count occupied bins (bins with stock > 0)
        occupied_bins = (
            self.db.query(func.count(func.distinct(BinStockLevel.bin_location_id)))
            .filter(
                BinStockLevel.bin_location_id.in_(descendant_ids),
                BinStockLevel.quantity_on_hand > 0,
            )
            .scalar()
            or 0
        )

        # Total capacity of bins in subtree
        total_capacity = self.db.query(func.sum(WarehouseLocation.capacity)).filter(
            WarehouseLocation.id.in_(descendant_ids),
            WarehouseLocation.location_type == LocationType.BIN.value,
            WarehouseLocation.is_active == True,  # noqa: E712
        ).scalar() or Decimal("0")

        # Used capacity (sum of stock in bins)
        used_capacity = self.db.query(func.sum(BinStockLevel.quantity_on_hand)).filter(
            BinStockLevel.bin_location_id.in_(descendant_ids),
            BinStockLevel.quantity_on_hand > 0,
        ).scalar() or Decimal("0")

        available_capacity = total_capacity - used_capacity

        # Distinct items in subtree
        distinct_items = (
            self.db.query(func.count(func.distinct(BinStockLevel.item_id)))
            .filter(
                BinStockLevel.bin_location_id.in_(descendant_ids),
                BinStockLevel.quantity_on_hand > 0,
            )
            .scalar()
            or 0
        )

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
            "distinct_items": distinct_items,
        }

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
