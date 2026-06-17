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
        reserved = {
            r.bin_location_id: r
            for r in self.reservation_service.get_active_reservations(
                org_id, warehouse_id
            )
        }
        expiring_bins = self._expiring_bin_ids(warehouse_id, org_id)

        def build_bin(loc: WarehouseLocation) -> dict:
            agg = bin_stock.get(loc.id, {"qty": Decimal("0"), "items": 0})
            capacity = Decimal(str(loc.capacity or 0))
            on_hand = agg["qty"]
            available = capacity - on_hand
            fill_pct = (
                round(float(on_hand / capacity) * 100, 1) if capacity > 0 else 0.0
            )
            res = reserved.get(loc.id)
            return {
                "id": loc.id,
                "code": loc.code,
                "full_path": loc.full_path,
                "position": self._position(loc),
                "capacity": float(capacity),
                "available_capacity": float(available),
                "fill_percentage": fill_pct,
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
                node["bins"] = [
                    build_bin(b) for b in kids if b.location_type == "bin"
                ]
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
        capacities = dict(
            self.db.query(WarehouseLocation.id, WarehouseLocation.capacity)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
                WarehouseLocation.location_type == "bin",
                WarehouseLocation.is_active.is_(True),
            )
            .all()
        )

        now = datetime.now(UTC)
        reservations = self.reservation_service.get_active_reservations(
            org_id, warehouse_id
        )
        reserved_by_bin = {r.bin_location_id: r for r in reservations}

        bins = []
        for bin_id, capacity in capacities.items():
            cap = Decimal(str(capacity or 0))
            on_hand = bin_stock.get(bin_id, {"qty": Decimal("0")})["qty"]
            fill_pct = round(float(on_hand / cap) * 100, 1) if cap > 0 else 0.0
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
                    "fill_percentage": fill_pct,
                    "is_reserved": res is not None,
                    "reserved_by": reserved_info,
                }
            )

        return {"bins": bins, "workers": []}

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

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
