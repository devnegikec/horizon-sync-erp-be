"""BinCapacityService — per-bin volume/weight capacity, rollup, availability.

Design: BIN_VOLUME_CAPACITY_SERVICE_DESIGN.md

The service is read-mostly and side-effect-light:
- ``refresh_bin`` / ``refresh_warehouse`` recompute cached ``%``, ``bin_state``
  and ``is_available`` on the bin row, then publish a ``bin.state.changed``
  Redis event for the 3-D view.
- ``get_capacity_tree`` / ``get_bin_capacity`` / ``get_bin_states`` compute
  occupancy on demand (bin ancestors are aggregated on read, not cached).
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import redis_pubsub
from app.core.exceptions import NotFoundError
from app.models.bin_reservation import BinReservation
from app.models.bin_stock_level import BinStockLevel
from app.models.warehouse import Warehouse
from app.models.warehouse_location import WarehouseLocation
from app.services.capacity_math import (
    CC_PER_M3,
    G_PER_KG,
    compute_bin_counts,
    compute_bin_occupancy,
    compute_item_required_cc_and_grams,
    compute_warehouse_bin_counts,
    compute_warehouse_bin_occupancy,
    effective_available_capacity,
    effective_bin_count_capacity,
    effective_bin_volume_limit_cc,
    effective_bin_weight_limit_g,
)

logger = logging.getLogger(__name__)

STATE_EMPTY = "empty"
STATE_AVAILABLE = "available"
STATE_ALMOST_FULL = "almost_full"
STATE_FULL = "full"

DEFAULT_FULL_THRESHOLD = Decimal("0.90")
DEFAULT_ALMOST_FULL_THRESHOLD = Decimal("0.70")


class BinCapacityService:
    """Compute and cache volume/weight capacity per bin and up the tree."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------ helpers

    def _get_bin(self, bin_id: UUID, org_id: UUID) -> WarehouseLocation:
        bin_loc = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id == bin_id,
                WarehouseLocation.organization_id == org_id,
                WarehouseLocation.location_type == "bin",
            )
            .first()
        )
        if bin_loc is None:
            raise NotFoundError(
                f"Bin {bin_id} not found",
                entity_type="WarehouseLocation",
                entity_id=str(bin_id),
            )
        return bin_loc

    def _get_warehouse(self, warehouse_id: UUID) -> Warehouse | None:
        return self.db.get(Warehouse, warehouse_id)

    @staticmethod
    def _use_volume(warehouse: Warehouse | None) -> bool:
        return (
            warehouse.use_volume
            if warehouse and warehouse.use_volume is not None
            else True
        )

    @staticmethod
    def _use_weight(warehouse: Warehouse | None) -> bool:
        return (
            warehouse.use_weight
            if warehouse and warehouse.use_weight is not None
            else False
        )

    def _effective_thresholds(
        self, bin_loc: WarehouseLocation, warehouse: Warehouse | None
    ) -> tuple[Decimal, Decimal]:
        full = bin_loc.full_threshold_pct
        if full is None and warehouse is not None:
            full = warehouse.full_threshold_pct
        if full is None:
            full = DEFAULT_FULL_THRESHOLD

        almost = bin_loc.almost_full_threshold_pct
        if almost is None and warehouse is not None:
            almost = warehouse.almost_full_threshold_pct
        if almost is None:
            almost = DEFAULT_ALMOST_FULL_THRESHOLD

        # Thresholds are stored as fractions (0.90 = 90%); binding_pct is a
        # percentage (0-100), so normalize both to percentage scale.
        return Decimal(str(full)) * 100, Decimal(str(almost)) * 100

    @staticmethod
    def _derive_state(binding_pct: Decimal, full: Decimal, almost: Decimal) -> str:
        if binding_pct is None or binding_pct <= 0:
            return STATE_EMPTY
        if binding_pct >= full:
            return STATE_FULL
        if binding_pct >= almost:
            return STATE_ALMOST_FULL
        return STATE_AVAILABLE

    def _compute_metrics(
        self,
        bin_loc: WarehouseLocation,
        warehouse: Warehouse | None,
        occupied_m3: Decimal,
        occupied_kg: Decimal,
    ) -> dict:
        use_volume = self._use_volume(warehouse)
        use_weight = self._use_weight(warehouse)

        # A bin's volume limit may live in ``max_volume_cc`` (layout designer)
        # or in ``capacity`` with ``capacity_uom='volume'`` (m³). Read both
        # through the shared helper so a 1.2 m³ bin is never mistaken for a
        # 1.2-item count.
        cap_m3 = None
        if use_volume:
            vol_limit_cc = effective_bin_volume_limit_cc(bin_loc)
            if vol_limit_cc is not None:
                cap_m3 = vol_limit_cc / CC_PER_M3

        cap_kg = None
        if use_weight:
            wt_limit_g = effective_bin_weight_limit_g(bin_loc)
            if wt_limit_g is not None:
                cap_kg = wt_limit_g / G_PER_KG

        vol_pct = (occupied_m3 / cap_m3 * 100) if cap_m3 else None
        wt_pct = (occupied_kg / cap_kg * 100) if cap_kg else None

        pcts = [p for p in (vol_pct, wt_pct) if p is not None]
        binding_pct = max(pcts) if pcts else Decimal("0")

        return {
            "occupied_m3": occupied_m3,
            "capacity_m3": cap_m3,
            "vol_pct": vol_pct,
            "occupied_kg": occupied_kg,
            "capacity_kg": cap_kg,
            "wt_pct": wt_pct,
            "binding_pct": binding_pct,
        }

    def _bin_counts(
        self,
        bin_loc: WarehouseLocation,
    ) -> tuple[Decimal, Decimal, Decimal | None, Decimal | None]:
        """Return (unit_count, master_pack_count, count_capacity, count_pct).

        ``count_capacity`` is the legacy *unit-count* limit and is only applied
        when the bin does not carry a physical (volume/weight) capacity.
        """
        units, packs = compute_bin_counts(self.db, bin_loc.id)
        cap = effective_bin_count_capacity(bin_loc)
        pct = (units / cap * 100) if cap else None
        return units, packs, cap, pct

    def _response_for_bin(
        self,
        bin_loc: WarehouseLocation,
        metrics: dict,
        state: str,
        is_available: bool,
    ) -> dict:
        units, packs, count_cap, count_pct = self._bin_counts(bin_loc)
        return {
            "bin_id": bin_loc.id,
            "warehouse_id": bin_loc.warehouse_id,
            "code": bin_loc.code,
            "full_path": bin_loc.full_path,
            "volume": {
                "occupied_m3": metrics["occupied_m3"],
                "capacity_m3": metrics["capacity_m3"],
                "pct": metrics["vol_pct"],
            },
            "weight": {
                "occupied_kg": metrics["occupied_kg"],
                "capacity_kg": metrics["capacity_kg"],
                "pct": metrics["wt_pct"],
            },
            "unit_count": units,
            "master_pack_count": packs,
            "count_capacity": count_cap,
            "count_pct": count_pct,
            "binding_pct": metrics["binding_pct"],
            "bin_state": state,
            "is_available": is_available,
        }

    def _evaluate_bin(
        self, bin_loc: WarehouseLocation, warehouse: Warehouse | None
    ) -> tuple[dict, str, bool]:
        occupied_m3, occupied_kg = compute_bin_occupancy(
            self.db,
            bin_loc.id,
            use_volume=self._use_volume(warehouse),
            use_weight=self._use_weight(warehouse),
        )
        metrics = self._compute_metrics(bin_loc, warehouse, occupied_m3, occupied_kg)
        full, almost = self._effective_thresholds(bin_loc, warehouse)
        state = self._derive_state(metrics["binding_pct"], full, almost)
        units, _packs, count_cap, _count_pct = self._bin_counts(bin_loc)
        is_available = self._is_available(
            bin_loc, metrics["binding_pct"], full, units, count_cap
        )
        return metrics, state, is_available

    @staticmethod
    def _is_available(
        bin_loc: WarehouseLocation,
        binding_pct: Decimal,
        full: Decimal,
        units: Decimal,
        count_cap: Decimal | None,
    ) -> bool:
        """Whether the bin can accept normal stock right now.

        A bin that is active but not pickable is a segregation location (HOLD /
        QUARANTINE); it must never be reported as available for normal put-away
        or picking, so ``is_pickable`` is part of the answer everywhere the flag
        is derived.
        """
        return (
            bool(bin_loc.is_active)
            and bool(bin_loc.is_pickable)
            and binding_pct < full
            and (count_cap is None or units < count_cap)
        )

    # ------------------------------------------------------------ refresh

    def refresh_bin(self, bin_id: UUID, org_id: UUID, publish: bool = True) -> dict:
        """Recompute and persist cached capacity state for one bin.

        ``publish=False`` skips the per-bin ``bin.state.changed`` event, for bulk
        callers that emit a single higher-level event instead (a layout apply
        already publishes ``layout.applied`` for the whole warehouse).
        """
        bin_loc = self._get_bin(bin_id, org_id)
        warehouse = self._get_warehouse(bin_loc.warehouse_id)
        metrics, state, is_available = self._evaluate_bin(bin_loc, warehouse)

        bin_loc.capacity_volume_pct = metrics["vol_pct"]
        bin_loc.capacity_weight_pct = metrics["wt_pct"]
        bin_loc.bin_state = state
        bin_loc.is_available = is_available
        # Keep the cached remaining capacity in the bin's own measure (units /
        # m³ / kg) so the location tree and bin pickers never show a stale or
        # unit-count-derived number for a volume-limited bin.
        units, _packs, _count_cap, _count_pct = self._bin_counts(bin_loc)
        bin_loc.available_capacity = effective_available_capacity(
            bin_loc,
            occupied_m3=metrics["occupied_m3"],
            occupied_kg=metrics["occupied_kg"],
            unit_count=units,
        )
        self.db.flush()

        if publish:
            try:
                redis_pubsub.publish_bin_event(
                    "bin.state.changed",
                    bin_id,
                    bin_loc.warehouse_id,
                    bin_state=state,
                    binding_pct=float(metrics["binding_pct"]),
                    is_available=is_available,
                )
            except Exception as exc:  # non-critical, never block the caller
                logger.warning("capacity event publish failed: %s", exc)

        return self._response_for_bin(bin_loc, metrics, state, is_available)

    def refresh_warehouse(
        self, warehouse_id: UUID, org_id: UUID, publish: bool = True
    ) -> int:
        """Recompute cached capacity for every active bin in a warehouse.

        This is the call that turns the freshly materialised physical limits of
        a layout apply (``max_volume_cc`` / ``capacity_uom='volume'``) into the
        cached state the 3-D view and bin pickers read: ``capacity_volume_pct``,
        ``bin_state``, ``is_available`` and ``available_capacity``.
        """
        bins = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
                WarehouseLocation.location_type == "bin",
                WarehouseLocation.is_active.is_(True),
            )
            .all()
        )
        for bin_loc in bins:
            self.refresh_bin(bin_loc.id, org_id, publish=publish)
        return len(bins)

    # ------------------------------------------------------------ reads

    def get_bin_capacity(self, bin_id: UUID, org_id: UUID) -> dict:
        """Live volume/weight capacity for one bin (not persisted)."""
        bin_loc = self._get_bin(bin_id, org_id)
        warehouse = self._get_warehouse(bin_loc.warehouse_id)
        metrics, state, is_available = self._evaluate_bin(bin_loc, warehouse)
        return self._response_for_bin(bin_loc, metrics, state, is_available)

    def get_bin_states(self, warehouse_id: UUID, org_id: UUID) -> list[dict]:
        """All bins with position + colour state for the 3-D view."""
        warehouse = self._get_warehouse(warehouse_id)
        bins = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
                WarehouseLocation.location_type == "bin",
                WarehouseLocation.is_active.is_(True),
            )
            .all()
        )
        occupancy = compute_warehouse_bin_occupancy(
            self.db,
            warehouse_id,
            use_volume=self._use_volume(warehouse),
            use_weight=self._use_weight(warehouse),
        )

        results: list[dict] = []
        for bin_loc in bins:
            occupied_m3, occupied_kg = occupancy.get(
                str(bin_loc.id), (Decimal("0"), Decimal("0"))
            )
            metrics = self._compute_metrics(
                bin_loc, warehouse, occupied_m3, occupied_kg
            )
            full, almost = self._effective_thresholds(bin_loc, warehouse)
            state = self._derive_state(metrics["binding_pct"], full, almost)
            units, _packs, count_cap, _count_pct = self._bin_counts(bin_loc)
            results.append(
                {
                    "bin_id": bin_loc.id,
                    "code": bin_loc.code,
                    "position_x": bin_loc.position_x,
                    "position_y": bin_loc.position_y,
                    "position_z": bin_loc.position_z,
                    "qr_code": bin_loc.qr_code,
                    "bin_state": state,
                    "binding_pct": metrics["binding_pct"],
                    "is_available": self._is_available(
                        bin_loc, metrics["binding_pct"], full, units, count_cap
                    ),
                }
            )
        return results

    def get_capacity_tree(self, warehouse_id: UUID, org_id: UUID) -> dict:
        """Full rollup tree: warehouse → zone → aisle → bay → level → bin."""
        warehouse = self._get_warehouse(warehouse_id)
        locations = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
                WarehouseLocation.is_active.is_(True),
            )
            .all()
        )
        occupancy = compute_warehouse_bin_occupancy(
            self.db,
            warehouse_id,
            use_volume=self._use_volume(warehouse),
            use_weight=self._use_weight(warehouse),
        )
        bin_counts = compute_warehouse_bin_counts(self.db, warehouse_id)

        # Pre-compute per-bin metrics.
        bin_metrics: dict[str, dict] = {}
        for loc in locations:
            if loc.location_type == "bin":
                om3, okg = occupancy.get(str(loc.id), (Decimal("0"), Decimal("0")))
                bin_metrics[str(loc.id)] = self._compute_metrics(
                    loc, warehouse, om3, okg
                )

        nodes: dict[str, dict] = {}
        for loc in locations:
            nodes[str(loc.id)] = {
                "node": str(loc.id),
                "level": loc.location_type,
                "code": loc.code,
                "full_path": loc.full_path,
                "volume": {
                    "occupied_m3": Decimal("0"),
                    "capacity_m3": None,
                    "pct": None,
                },
                "weight": {
                    "occupied_kg": Decimal("0"),
                    "capacity_kg": None,
                    "pct": None,
                },
                "unit_count": Decimal("0"),
                "master_pack_count": Decimal("0"),
                "count_capacity": None,
                "count_pct": None,
                "binding_pct": Decimal("0"),
                "bin_state": None,
                "is_available": None,
                "children": [],
                "_loc": loc,
                "_parent": str(loc.parent_location_id)
                if loc.parent_location_id
                else None,
            }

        for loc in locations:
            if loc.location_type == "bin":
                m = bin_metrics[str(loc.id)]
                full, almost = self._effective_thresholds(loc, warehouse)
                state = self._derive_state(m["binding_pct"], full, almost)
                n = nodes[str(loc.id)]
                n["volume"] = {
                    "occupied_m3": m["occupied_m3"],
                    "capacity_m3": m["capacity_m3"],
                    "pct": m["vol_pct"],
                }
                n["weight"] = {
                    "occupied_kg": m["occupied_kg"],
                    "capacity_kg": m["capacity_kg"],
                    "pct": m["wt_pct"],
                }
                n["binding_pct"] = m["binding_pct"]
                n["bin_state"] = state
                units, packs = bin_counts.get(str(loc.id), (Decimal("0"), Decimal("0")))
                count_cap = effective_bin_count_capacity(loc)
                n["is_available"] = self._is_available(
                    loc, m["binding_pct"], full, units, count_cap
                )
                n["unit_count"] = units
                n["master_pack_count"] = packs
                n["count_capacity"] = count_cap
                n["count_pct"] = (units / count_cap * 100) if count_cap else None

        roots: list[dict] = []
        for loc in locations:
            n = nodes[str(loc.id)]
            parent = n["_parent"]
            if parent is not None and parent in nodes:
                nodes[parent]["children"].append(n)
            else:
                roots.append(n)

        def aggregate(node: dict) -> None:
            occ_m3 = node["volume"]["occupied_m3"]
            cap_m3 = node["volume"]["capacity_m3"]
            occ_kg = node["weight"]["occupied_kg"]
            cap_kg = node["weight"]["capacity_kg"]
            units = node["unit_count"]
            packs = node["master_pack_count"]
            count_cap = node["count_capacity"]
            for child in node["children"]:
                aggregate(child)
                occ_m3 += child["volume"]["occupied_m3"]
                if child["volume"]["capacity_m3"] is not None:
                    cap_m3 = (cap_m3 or Decimal("0")) + child["volume"]["capacity_m3"]
                occ_kg += child["weight"]["occupied_kg"]
                if child["weight"]["capacity_kg"] is not None:
                    cap_kg = (cap_kg or Decimal("0")) + child["weight"]["capacity_kg"]
                units += child["unit_count"]
                packs += child["master_pack_count"]
                if child["count_capacity"] is not None:
                    count_cap = (count_cap or Decimal("0")) + child["count_capacity"]
            node["volume"]["occupied_m3"] = occ_m3
            node["volume"]["capacity_m3"] = cap_m3
            node["volume"]["pct"] = (occ_m3 / cap_m3 * 100) if cap_m3 else None
            node["weight"]["occupied_kg"] = occ_kg
            node["weight"]["capacity_kg"] = cap_kg
            node["weight"]["pct"] = (occ_kg / cap_kg * 100) if cap_kg else None
            node["unit_count"] = units
            node["master_pack_count"] = packs
            node["count_capacity"] = count_cap
            node["count_pct"] = (units / count_cap * 100) if count_cap else None
            pcts = [
                p
                for p in (node["volume"]["pct"], node["weight"]["pct"])
                if p is not None
            ]
            node["binding_pct"] = max(pcts) if pcts else Decimal("0")

        for root in roots:
            aggregate(root)

        def clean(node: dict) -> dict:
            return {
                "node": node["node"],
                "level": node["level"],
                "code": node["code"],
                "full_path": node["full_path"],
                "volume": node["volume"],
                "weight": node["weight"],
                "unit_count": node["unit_count"],
                "master_pack_count": node["master_pack_count"],
                "count_capacity": node["count_capacity"],
                "count_pct": node["count_pct"],
                "binding_pct": node["binding_pct"],
                "bin_state": node["bin_state"],
                "is_available": node["is_available"],
                "children": [clean(c) for c in node["children"]],
            }

        children = [clean(r) for r in roots]
        # Warehouse root aggregates its top-level children.
        total_m3 = sum((c["volume"]["occupied_m3"] for c in children), Decimal("0"))
        total_cap_m3 = None
        for c in children:
            if c["volume"]["capacity_m3"] is not None:
                total_cap_m3 = (total_cap_m3 or Decimal("0")) + c["volume"][
                    "capacity_m3"
                ]
        total_kg = sum((c["weight"]["occupied_kg"] for c in children), Decimal("0"))
        total_cap_kg = None
        for c in children:
            if c["weight"]["capacity_kg"] is not None:
                total_cap_kg = (total_cap_kg or Decimal("0")) + c["weight"][
                    "capacity_kg"
                ]
        total_units = sum((c["unit_count"] for c in children), Decimal("0"))
        total_packs = sum((c["master_pack_count"] for c in children), Decimal("0"))
        total_count_cap = None
        for c in children:
            if c["count_capacity"] is not None:
                total_count_cap = (total_count_cap or Decimal("0")) + c[
                    "count_capacity"
                ]
        pcts = [
            p
            for p in (
                (total_m3 / total_cap_m3 * 100) if total_cap_m3 else None,
                (total_kg / total_cap_kg * 100) if total_cap_kg else None,
            )
            if p is not None
        ]

        return {
            "node": str(warehouse_id),
            "level": "warehouse",
            "code": warehouse.code if warehouse else str(warehouse_id),
            "full_path": None,
            "volume": {
                "occupied_m3": total_m3,
                "capacity_m3": total_cap_m3,
                "pct": (total_m3 / total_cap_m3 * 100) if total_cap_m3 else None,
            },
            "weight": {
                "occupied_kg": total_kg,
                "capacity_kg": total_cap_kg,
                "pct": (total_kg / total_cap_kg * 100) if total_cap_kg else None,
            },
            "unit_count": total_units,
            "master_pack_count": total_packs,
            "count_capacity": total_count_cap,
            "count_pct": (total_units / total_count_cap * 100)
            if total_count_cap
            else None,
            "binding_pct": max(pcts) if pcts else Decimal("0"),
            "bin_state": None,
            "is_available": None,
            "children": children,
        }

    # ------------------------------------------------------------ availability

    def _reserved_bin_ids(self, org_id: UUID) -> set[str]:
        now = datetime.now(UTC)
        rows = (
            self.db.query(BinReservation.bin_location_id)
            .filter(
                BinReservation.organization_id == org_id,
                BinReservation.released_at.is_(None),
                BinReservation.expires_at > now,
            )
            .all()
        )
        return {str(r[0]) for r in rows}

    def _required_cc_and_grams(
        self, item_id: UUID | None, qty
    ) -> tuple[Decimal | None, Decimal | None]:
        """Required volume (cc) and weight (g) for an incoming put-away.

        Master-pack aware: an intact carton occupies its outer volume, not
        ``conversion_factor`` × base-unit volume — the same math the occupancy
        engine uses, so a fit check compares like with like. ``None`` for a
        dimension means it cannot be measured (unconstrained).
        """
        if item_id is None or qty is None:
            return None, None
        return compute_item_required_cc_and_grams(self.db, item_id, None, qty)

    def _required_fits(
        self,
        bin_loc: WarehouseLocation,
        warehouse: Warehouse | None,
        occupied_m3: Decimal,
        occupied_kg: Decimal,
        required_cc: Decimal | None,
        required_g: Decimal | None,
    ) -> bool:
        """Whether the bin still has room for the required volume *and* weight.

        Both dimensions are checked (each only when the warehouse enables it and
        the bin carries a limit), so a weight-limited bin is not accepted merely
        because the item's volume happens to fit.
        """
        if self._use_volume(warehouse) and required_cc is not None:
            limit_cc = effective_bin_volume_limit_cc(bin_loc)
            if limit_cc is not None:
                if occupied_m3 * CC_PER_M3 + required_cc > limit_cc:
                    return False
        if self._use_weight(warehouse) and required_g is not None:
            limit_g = effective_bin_weight_limit_g(bin_loc)
            if limit_g is not None:
                if occupied_kg * G_PER_KG + required_g > limit_g:
                    return False
        return True

    def get_available_bins(
        self,
        warehouse_id: UUID,
        org_id: UUID,
        task_type: str = "put_away",
        item_id: UUID | None = None,
        qty=None,
    ) -> list[dict]:
        """Availability-filtered candidate bins for put-away or pick."""
        warehouse = self._get_warehouse(warehouse_id)
        reserved = self._reserved_bin_ids(org_id)
        required_cc, required_g = (
            self._required_cc_and_grams(item_id, qty)
            if task_type == "put_away"
            else (None, None)
        )

        bins = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
                WarehouseLocation.location_type == "bin",
                WarehouseLocation.is_active.is_(True),
                # Segregation bins (HOLD / QUARANTINE) are active but not
                # pickable — normal put-away and picking must never target them.
                WarehouseLocation.is_pickable.is_(True),
            )
            .all()
        )

        results: list[dict] = []
        for bin_loc in bins:
            if str(bin_loc.id) in reserved:
                continue

            occupied_m3, occupied_kg = compute_bin_occupancy(
                self.db,
                bin_loc.id,
                use_volume=self._use_volume(warehouse),
                use_weight=self._use_weight(warehouse),
            )
            metrics = self._compute_metrics(
                bin_loc, warehouse, occupied_m3, occupied_kg
            )
            full, almost = self._effective_thresholds(bin_loc, warehouse)
            state = self._derive_state(metrics["binding_pct"], full, almost)

            if task_type == "pick":
                has_stock = (
                    self.db.query(BinStockLevel.id)
                    .filter(
                        BinStockLevel.bin_location_id == bin_loc.id,
                        BinStockLevel.quantity_on_hand > 0,
                    )
                    .first()
                    is not None
                )
                if not has_stock:
                    continue
                available = True
            else:  # put_away
                if metrics["binding_pct"] >= full:
                    continue
                if not self._required_fits(
                    bin_loc,
                    warehouse,
                    occupied_m3,
                    occupied_kg,
                    required_cc,
                    required_g,
                ):
                    continue
                available = True

            results.append(
                {
                    "bin_id": bin_loc.id,
                    "code": bin_loc.code,
                    "full_path": bin_loc.full_path,
                    "bin_state": state,
                    "binding_pct": metrics["binding_pct"],
                    "remaining_m3": (
                        metrics["capacity_m3"] - occupied_m3
                        if metrics["capacity_m3"] is not None
                        else None
                    ),
                    "is_available": available,
                }
            )
        return results
