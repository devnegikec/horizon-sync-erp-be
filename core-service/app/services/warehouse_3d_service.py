"""3D warehouse view service.

Assembles the procedurally-generated geometry tree (zones → aisles → bays →
levels → bins) consumed by the React Three Fiber frontend, and a lightweight
live-status snapshot (fill %, reservation state) used as a WebSocket fallback.

Design ref: docs/3D_WAREHOUSE_VIEW_DESIGN.md sections 5.1, 5.2
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.bin_stock_level import BinStockLevel
from app.models.warehouse import Warehouse
from app.models.warehouse_location import WarehouseLocation
from app.services.bin_reservation_service import BinReservationService
from app.services.capacity_math import (
    CC_PER_M3,
    G_PER_KG,
    compute_warehouse_bin_occupancy,
    display_capacity_uom,
    effective_bin_count_capacity,
    effective_bin_volume_limit_cc,
    effective_bin_weight_limit_g,
)

EXPIRY_WARNING_DAYS = 30  # FR-FE-03


class Warehouse3DService:
    """Builds 3D layout geometry and live bin status for a warehouse."""

    def __init__(self, db: Session):
        self.db = db
        self.reservation_service = BinReservationService(db)

    # ------------------------------------------------------------------
    # LAYOUT (section 5.1)
    # ------------------------------------------------------------------

    def get_layout(self, warehouse_id: UUID, org_id: UUID) -> dict:
        """Return the full geometry tree for a warehouse."""
        warehouse = (
            self.db.query(Warehouse)
            .filter(Warehouse.id == warehouse_id, Warehouse.organization_id == org_id)
            .first()
        )
        if warehouse is None:
            raise NotFoundError(
                message="Warehouse not found",
                entity_type="Warehouse",
                entity_id=str(warehouse_id),
            )

        locations = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
                WarehouseLocation.is_active.is_(True),
            )
            .all()
        )

        # Index locations by parent for hierarchy assembly.
        children_by_parent: dict[UUID | None, list[WarehouseLocation]] = {}
        for loc in locations:
            children_by_parent.setdefault(loc.parent_location_id, []).append(loc)

        # Pre-compute per-bin stock aggregates and reservation state.
        bin_stock = self._bin_stock_map(warehouse_id, org_id)
        occupancy = compute_warehouse_bin_occupancy(
            self.db,
            warehouse_id,
            use_volume=self._use_volume(warehouse),
            use_weight=self._use_weight(warehouse),
        )
        reserved = {
            r.bin_location_id: r
            for r in self.reservation_service.get_active_reservations(
                org_id, warehouse_id
            )
        }
        expiring_bins = self._expiring_bin_ids(warehouse_id, org_id)

        def build_bin(loc: WarehouseLocation) -> dict:
            agg = bin_stock.get(loc.id, {"qty": Decimal("0"), "items": 0})
            on_hand = agg["qty"]
            occ_m3, occ_kg = occupancy.get(str(loc.id), (Decimal("0"), Decimal("0")))
            metrics = self._fill_metrics(warehouse, loc, occ_m3, occ_kg, on_hand)
            res = reserved.get(loc.id)
            return {
                "id": loc.id,
                "code": loc.code,
                "full_path": loc.full_path,
                "position": self._position(loc),
                "capacity": metrics["capacity"],
                "available_capacity": metrics["available_capacity"],
                "capacity_uom": metrics["capacity_uom"],
                "volume": metrics["volume"],
                "weight": metrics["weight"],
                "fill_percentage": metrics["fill_percentage"],
                "is_active": bool(loc.is_active),
                "is_reserved": res is not None,
                "reserved_by_worker_id": res.worker_id if res else None,
                "items_count": agg["items"],
                "has_expiring_items": loc.id in expiring_bins,
            }

        def build_subtree(loc: WarehouseLocation) -> dict:
            node = {
                "id": loc.id,
                "code": loc.code,
                "name": loc.name,
                "position": self._position(loc),
            }
            kids = children_by_parent.get(loc.id, [])
            if loc.location_type == "level":
                node["bins"] = [build_bin(b) for b in kids if b.location_type == "bin"]
            elif loc.location_type == "bay":
                node["levels"] = [
                    build_subtree(c) for c in kids if c.location_type == "level"
                ]
            elif loc.location_type == "aisle":
                node["orientation"] = getattr(loc, "orientation", None)
                node["bays"] = [
                    build_subtree(c) for c in kids if c.location_type == "bay"
                ]
            elif loc.location_type == "zone":
                node["aisles"] = [
                    build_subtree(c) for c in kids if c.location_type == "aisle"
                ]
            return node

        zones = [
            build_subtree(z)
            for z in children_by_parent.get(None, [])
            if z.location_type == "zone"
        ]

        return {
            "warehouse": {
                "id": warehouse.id,
                "name": warehouse.name,
                "code": warehouse.code,
            },
            "zones": zones,
        }

    # ------------------------------------------------------------------
    # LIVE STATUS (section 5.2)
    # ------------------------------------------------------------------

    def get_status(self, warehouse_id: UUID, org_id: UUID) -> dict:
        """Return current bin fill/reservation status for polling clients."""
        bin_stock = self._bin_stock_map(warehouse_id, org_id)
        warehouse = self.db.get(Warehouse, warehouse_id)
        bin_locations = (
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

        now = datetime.now(UTC)
        reservations = self.reservation_service.get_active_reservations(
            org_id, warehouse_id
        )
        reserved_by_bin = {r.bin_location_id: r for r in reservations}

        bins = []
        for bin_loc in bin_locations:
            bin_id = bin_loc.id
            on_hand = bin_stock.get(bin_id, {"qty": Decimal("0")})["qty"]
            occ_m3, occ_kg = occupancy.get(str(bin_id), (Decimal("0"), Decimal("0")))
            metrics = self._fill_metrics(warehouse, bin_loc, occ_m3, occ_kg, on_hand)
            res = reserved_by_bin.get(bin_id)
            reserved_info = None
            if res is not None:
                expires_in = self._expires_in_seconds(res.expires_at, now)
                reserved_info = {
                    "worker_id": res.worker_id,
                    "expires_in_seconds": expires_in,
                }
            bins.append(
                {
                    "bin_id": bin_id,
                    "capacity": metrics["capacity"],
                    "available_capacity": metrics["available_capacity"],
                    "capacity_uom": metrics["capacity_uom"],
                    "volume": metrics["volume"],
                    "weight": metrics["weight"],
                    "fill_percentage": metrics["fill_percentage"],
                    "is_reserved": res is not None,
                    "reserved_by": reserved_info,
                }
            )

        return {"bins": bins, "workers": []}

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _use_volume(warehouse: Warehouse | None) -> bool:
        return (
            warehouse.use_volume
            if warehouse is not None and warehouse.use_volume is not None
            else True
        )

    @staticmethod
    def _use_weight(warehouse: Warehouse | None) -> bool:
        return (
            warehouse.use_weight
            if warehouse is not None and warehouse.use_weight is not None
            else False
        )

    def _fill_metrics(
        self,
        warehouse: Warehouse | None,
        bin_loc: WarehouseLocation,
        occupied_m3: Decimal,
        occupied_kg: Decimal,
        on_hand: Decimal,
    ) -> dict:
        """Volume/weight-aware capacity view for one bin.

        ``capacity`` / ``available_capacity`` are reported **in the bin's own
        measure**, described by ``capacity_uom``:

        * a count-limited bin → units (legacy behaviour),
        * a volume-limited bin (``max_volume_cc``, or ``capacity`` with
          ``capacity_uom='volume'``) → m³,
        * a weight-limited bin → kg.

        This matters because new-layout bins carry ``capacity = 1.2`` m³, so
        reporting a unit count would either be wrong or a constant ``0`` that
        never moves when stock is stored. ``fill_percentage`` and the ``volume``
        / ``weight`` blocks are the physical measures.
        """
        cap_m3 = None
        if self._use_volume(warehouse):
            limit_cc = effective_bin_volume_limit_cc(bin_loc)
            if limit_cc is not None:
                cap_m3 = limit_cc / CC_PER_M3
        cap_kg = None
        if self._use_weight(warehouse):
            limit_g = effective_bin_weight_limit_g(bin_loc)
            if limit_g is not None:
                cap_kg = limit_g / G_PER_KG

        available_m3 = (cap_m3 - occupied_m3) if cap_m3 is not None else None
        available_kg = (cap_kg - occupied_kg) if cap_kg is not None else None

        count_cap = effective_bin_count_capacity(bin_loc)
        if count_cap is not None:
            capacity = Decimal(str(count_cap))
            available = capacity - on_hand
            capacity_uom = bin_loc.capacity_uom or "units"
        elif available_m3 is not None:
            capacity = cap_m3
            available = available_m3
            capacity_uom = "volume"
        elif available_kg is not None:
            capacity = cap_kg
            available = available_kg
            capacity_uom = "weight"
        else:
            capacity = Decimal("0")
            available = Decimal("0")
            capacity_uom = bin_loc.capacity_uom

        vol_pct = (occupied_m3 / cap_m3 * 100) if cap_m3 else None
        wt_pct = (occupied_kg / cap_kg * 100) if cap_kg else None
        pcts = [p for p in (vol_pct, wt_pct) if p is not None]
        if pcts:
            binding = max(pcts)
        else:
            binding = (
                (Decimal(str(on_hand)) / capacity * 100)
                if capacity > 0
                else Decimal("0")
            )

        return {
            "capacity": float(capacity),
            "available_capacity": float(available),
            # "volume"/"weight" is the internal bin vocabulary; the number is
            # already in m³/kg, so report the matching unit.
            "capacity_uom": display_capacity_uom(capacity_uom),
            "fill_percentage": round(float(binding), 1),
            "volume": {
                "capacity_m3": float(cap_m3) if cap_m3 is not None else None,
                "occupied_m3": float(occupied_m3),
                "available_m3": float(available_m3)
                if available_m3 is not None
                else None,
                "pct": round(float(vol_pct), 1) if vol_pct is not None else None,
            },
            "weight": {
                "capacity_kg": float(cap_kg) if cap_kg is not None else None,
                "occupied_kg": float(occupied_kg),
                "available_kg": float(available_kg)
                if available_kg is not None
                else None,
                "pct": round(float(wt_pct), 1) if wt_pct is not None else None,
            },
        }

    def _bin_stock_map(self, warehouse_id: UUID, org_id: UUID) -> dict[UUID, dict]:
        """Map bin_location_id -> {qty, items} for the warehouse."""
        rows = (
            self.db.query(
                BinStockLevel.bin_location_id,
                func.coalesce(func.sum(BinStockLevel.quantity_on_hand), 0),
                func.count(func.distinct(BinStockLevel.item_id)),
            )
            .join(
                WarehouseLocation,
                BinStockLevel.bin_location_id == WarehouseLocation.id,
            )
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                BinStockLevel.organization_id == org_id,
                BinStockLevel.quantity_on_hand > 0,
            )
            .group_by(BinStockLevel.bin_location_id)
            .all()
        )
        return {
            row[0]: {"qty": Decimal(str(row[1] or 0)), "items": int(row[2] or 0)}
            for row in rows
        }

    def _expiring_bin_ids(self, warehouse_id: UUID, org_id: UUID) -> set[UUID]:
        """Bins holding stock expiring within EXPIRY_WARNING_DAYS (FR-FE-03)."""
        cutoff = datetime.now(UTC).date() + timedelta(days=EXPIRY_WARNING_DAYS)
        rows = (
            self.db.query(BinStockLevel.bin_location_id)
            .join(
                WarehouseLocation,
                BinStockLevel.bin_location_id == WarehouseLocation.id,
            )
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                BinStockLevel.organization_id == org_id,
                BinStockLevel.quantity_on_hand > 0,
                BinStockLevel.expiry_date.isnot(None),
                BinStockLevel.expiry_date <= cutoff,
            )
            .distinct()
            .all()
        )
        return {row[0] for row in rows}

    @staticmethod
    def _position(loc: WarehouseLocation) -> dict:
        return {
            "x": float(loc.position_x or 0),
            "y": float(loc.position_y or 0),
            "z": float(loc.position_z or 0),
        }

    @staticmethod
    def _expires_in_seconds(expires_at: datetime, now: datetime) -> int:
        if expires_at is None:
            return 0
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return max(0, int((expires_at - now).total_seconds()))

    # ------------------------------------------------------------------
    # BIN STOCK DETAIL (FR-3D-04)
    # ------------------------------------------------------------------

    def get_bin_stock_detail(self, bin_id: UUID, org_id: UUID) -> dict:
        """Return individual item records stored in a specific bin.

        Implements FR-3D-04: clicking a bin shows items stored with name,
        SKU, quantity, batch number, and expiry date.
        """
        from app.models.item import Item

        # Verify the bin exists and belongs to this org
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
                message="Bin location not found",
                entity_type="WarehouseLocation",
                entity_id=str(bin_id),
            )

        rows = (
            self.db.query(
                BinStockLevel.item_id,
                Item.item_name,
                Item.item_code,
                Item.sku,
                Item.uom,
                BinStockLevel.quantity_on_hand,
                BinStockLevel.inventory_status,
                BinStockLevel.batch_number,
                BinStockLevel.expiry_date,
                BinStockLevel.created_at,
            )
            .join(Item, BinStockLevel.item_id == Item.id)
            .filter(
                BinStockLevel.bin_location_id == bin_id,
                BinStockLevel.organization_id == org_id,
                BinStockLevel.quantity_on_hand > 0,
            )
            .order_by(
                BinStockLevel.expiry_date.asc().nullslast(),
                BinStockLevel.created_at.asc(),
            )
            .all()
        )

        items = []
        total_qty = Decimal("0")
        for row in rows:
            qty = Decimal(str(row[5] or 0))
            total_qty += qty
            items.append(
                {
                    "item_id": row[0],
                    "item_name": row[1],
                    "item_code": row[2],
                    "sku": row[3],
                    "uom": row[4],
                    "quantity_on_hand": float(qty),
                    "inventory_status": row[6] or "available",
                    "batch_number": row[7],
                    "expiry_date": row[8].isoformat() if row[8] else None,
                    "created_at": row[9].isoformat() if row[9] else None,
                }
            )

        return {
            "bin_id": bin_id,
            "bin_code": bin_loc.code,
            "items": items,
            "total_quantity": float(total_qty),
            "total_items": len(items),
        }
