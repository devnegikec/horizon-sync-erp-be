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
from app.models.item_packaging_unit import ItemPackagingUnit
from app.models.warehouse import Warehouse
from app.models.warehouse_location import WarehouseLocation
from app.services.capacity_math import (
    CC_PER_M3,
    G_PER_KG,
    MM3_PER_M3,
    compute_bin_occupancy,
    compute_warehouse_bin_occupancy,
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

        cap_m3 = None
        if use_volume and bin_loc.max_volume_cc is not None:
            cap_m3 = Decimal(str(bin_loc.max_volume_cc)) / CC_PER_M3

        cap_kg = None
        if use_weight and bin_loc.max_weight_grams is not None:
            cap_kg = Decimal(str(bin_loc.max_weight_grams)) / G_PER_KG

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

    def _response_for_bin(
        self,
        bin_loc: WarehouseLocation,
        metrics: dict,
        state: str,
        is_available: bool,
    ) -> dict:
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
        is_available = bool(bin_loc.is_active) and metrics["binding_pct"] < full
        return metrics, state, is_available

    # ------------------------------------------------------------ refresh

    def refresh_bin(self, bin_id: UUID, org_id: UUID) -> dict:
        """Recompute and persist cached capacity state for one bin."""
        bin_loc = self._get_bin(bin_id, org_id)
        warehouse = self._get_warehouse(bin_loc.warehouse_id)
        metrics, state, is_available = self._evaluate_bin(bin_loc, warehouse)

        bin_loc.capacity_volume_pct = metrics["vol_pct"]
        bin_loc.capacity_weight_pct = metrics["wt_pct"]
        bin_loc.bin_state = state
        bin_loc.is_available = is_available
        self.db.flush()

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

    def refresh_warehouse(self, warehouse_id: UUID, org_id: UUID) -> int:
        """Recompute cached capacity for every bin in a warehouse."""
        bins = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
                WarehouseLocation.location_type == "bin",
            )
            .all()
        )
        for bin_loc in bins:
            self.refresh_bin(bin_loc.id, org_id)
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
                    "is_available": bool(bin_loc.is_active)
                    and metrics["binding_pct"] < full,
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
            )
            .all()
        )
        occupancy = compute_warehouse_bin_occupancy(
            self.db,
            warehouse_id,
            use_volume=self._use_volume(warehouse),
            use_weight=self._use_weight(warehouse),
        )

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
                n["is_available"] = bool(loc.is_active) and m["binding_pct"] < full

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
            for child in node["children"]:
                aggregate(child)
                occ_m3 += child["volume"]["occupied_m3"]
                if child["volume"]["capacity_m3"] is not None:
                    cap_m3 = (cap_m3 or Decimal("0")) + child["volume"]["capacity_m3"]
                occ_kg += child["weight"]["occupied_kg"]
                if child["weight"]["capacity_kg"] is not None:
                    cap_kg = (cap_kg or Decimal("0")) + child["weight"]["capacity_kg"]
            node["volume"]["occupied_m3"] = occ_m3
            node["volume"]["capacity_m3"] = cap_m3
            node["volume"]["pct"] = (occ_m3 / cap_m3 * 100) if cap_m3 else None
            node["weight"]["occupied_kg"] = occ_kg
            node["weight"]["capacity_kg"] = cap_kg
            node["weight"]["pct"] = (occ_kg / cap_kg * 100) if cap_kg else None
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

    def _required_volume_m3(self, item_id: UUID | None, qty) -> Decimal | None:
        """Required m³ for an incoming put-away (None when unknown)."""
        if item_id is None or qty is None:
            return None
        base = (
            self.db.query(ItemPackagingUnit)
            .filter(
                ItemPackagingUnit.item_id == item_id,
                ItemPackagingUnit.is_base_unit.is_(True),
            )
            .first()
        )
        if base is None or not (base.length_mm and base.width_mm and base.height_mm):
            return None
        mm3 = (
            Decimal(str(qty))
            * Decimal(str(base.length_mm))
            * Decimal(str(base.width_mm))
            * Decimal(str(base.height_mm))
        )
        return mm3 / MM3_PER_M3

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
        required_m3 = (
            self._required_volume_m3(item_id, qty) if task_type == "put_away" else None
        )

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
                if required_m3 is not None and metrics["capacity_m3"] is not None:
                    remaining = metrics["capacity_m3"] - occupied_m3
                    if required_m3 > remaining:
                        continue
                available = True

            results.append(
                {
                    "bin_id": bin_loc.id,
                    "code": bin_loc.code,
                    "full_path": bin_loc.full_path,
                    "bin_state": state,
                    "binding_pct": metrics["binding_pct"],
                    "is_available": available,
                }
            )
        return results
