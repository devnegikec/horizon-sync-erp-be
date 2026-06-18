"""Smart location suggestion engine for put-away and picking.

Ranks candidate bins so workers are directed to the optimal location while
avoiding contention with other workers (reserved bins are excluded) and
honouring allocation rules, capacity, proximity, FEFO/FIFO and consolidation.

Scoring follows docs/3D_WAREHOUSE_VIEW_DESIGN.md section 7. Where the warehouse
floor plan (dock door coordinates) is not yet configured — Phase 0 — the dock
position defaults to the origin (0, 0, 0).

Design ref: docs/3D_WAREHOUSE_VIEW_DESIGN.md sections 3.2, 7
"""

import math
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.bin_stock_level import BinStockLevel
from app.models.item import Item
from app.models.location_allocation import LocationAllocation
from app.models.warehouse_location import WarehouseLocation
from app.services.bin_reservation_service import BinReservationService

Position = tuple[float, float, float]


class LocationSuggestionService:
    """Produces ranked bin suggestions for put-away and pick tasks."""

    def __init__(self, db: Session):
        self.db = db
        self.reservation_service = BinReservationService(db)

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def suggest(
        self,
        task_type: str,
        item_id: UUID,
        quantity: Decimal,
        warehouse_id: UUID,
        worker_id: UUID,
        org_id: UUID,
        batch_number: str | None = None,
        exclude_bin_ids: list[UUID] | None = None,
        worker_position: Position | None = None,
        limit: int = 10,
    ) -> dict:
        """Return ranked bin suggestions for a put-away or pick task.

        Args:
            task_type: 'put_away' or 'pick'.
            item_id: The item being put away or picked.
            quantity: Quantity needed.
            warehouse_id: Warehouse scope.
            worker_id: The requesting worker (their own reservations are not
                treated as obstacles).
            org_id: Organization scope.
            batch_number: Optional batch hint (pick).
            exclude_bin_ids: Bins the worker already skipped.
            worker_position: Current (x, y, z) of the worker; defaults to dock.
            limit: Max number of suggestions to return.

        Returns:
            Dict with ranked ``suggestions`` and evaluation metadata.
        """
        item = (
            self.db.query(Item)
            .filter(Item.id == item_id, Item.organization_id == org_id)
            .first()
        )
        if item is None:
            raise NotFoundError(
                message="Item not found",
                entity_type="Item",
                entity_id=str(item_id),
            )

        excluded = set(exclude_bin_ids or [])
        reserved_bin_ids = self.reservation_service.get_reserved_bin_ids(
            org_id=org_id,
            warehouse_id=warehouse_id,
            exclude_worker_id=worker_id,
        )
        dock_position = self._get_dock_position(warehouse_id, org_id)
        origin = worker_position or dock_position
        max_distance = self._get_max_distance(warehouse_id, org_id)

        if task_type == "put_away":
            scored = self._score_put_away(
                item=item,
                quantity=Decimal(str(quantity)),
                warehouse_id=warehouse_id,
                org_id=org_id,
                reserved_bin_ids=reserved_bin_ids,
                excluded=excluded,
                worker_position=origin,
                dock_position=dock_position,
                max_distance=max_distance,
            )
            strategy = "put_away_scored"
        elif task_type == "pick":
            scored = self._score_pick(
                item=item,
                quantity=Decimal(str(quantity)),
                warehouse_id=warehouse_id,
                org_id=org_id,
                batch_number=batch_number,
                reserved_bin_ids=reserved_bin_ids,
                excluded=excluded,
                worker_position=origin,
                max_distance=max_distance,
            )
            strategy = "pick_fefo_fifo"
        else:
            from app.core.exceptions import ValidationError

            raise ValidationError("task_type must be 'put_away' or 'pick'")

        total_candidates = len(scored)
        scored.sort(key=lambda s: s["score"], reverse=True)
        top = scored[:limit]
        for rank, s in enumerate(top, start=1):
            s["rank"] = rank

        return {
            "suggestions": top,
            "strategy_used": strategy,
            "total_candidates_evaluated": total_candidates,
            "excluded_bins": len(excluded),
        }

    # ------------------------------------------------------------------
    # PUT-AWAY SCORING (section 7.1)
    # ------------------------------------------------------------------

    def _score_put_away(
        self,
        item: Item,
        quantity: Decimal,
        warehouse_id: UUID,
        org_id: UUID,
        reserved_bin_ids: set[UUID],
        excluded: set[UUID],
        worker_position: Position,
        dock_position: Position,
        max_distance: float,
    ) -> list[dict]:
        item_group_id = item.item_group_id

        # Allocation lookups for this item group.
        exclusive_loc_ids = self._allocated_location_ids(
            org_id, item_group_id, "exclusive"
        ) if item_group_id else set()
        preferred_loc_ids = self._allocated_location_ids(
            org_id, item_group_id, "preferred"
        ) if item_group_id else set()
        # Bins exclusively allocated to *any* group (blocked for this item
        # unless the allocation belongs to this item's group).
        all_exclusive_loc_ids = self._allocated_location_ids(
            org_id, None, "exclusive"
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
        for b in bins:
            if b.id in excluded or b.id in reserved_bin_ids:
                continue

            reasons: list[str] = []
            score = 0.0

            # 1. Allocation match
            if b.id in exclusive_loc_ids:
                score += 100
                reasons.append("Exclusive allocation match")
            elif b.id in preferred_loc_ids:
                score += 50
                reasons.append("Preferred allocation match")
            elif b.id in all_exclusive_loc_ids:
                # Exclusively allocated to a different group — skip.
                continue

            # 2. Capacity
            available = self._available_capacity(b)
            if available < quantity:
                continue
            total_capacity = Decimal(str(b.capacity or 0))
            if total_capacity > 0:
                capacity_ratio = float(available / total_capacity)
                score += capacity_ratio * 10
                reasons.append(f"{round(capacity_ratio * 100)}% capacity available")

            # 3. Proximity to dock
            dist_to_dock = self._distance(self._position(b), dock_position)
            if max_distance > 0:
                proximity = (1 - min(dist_to_dock / max_distance, 1.0)) * 5
                score += proximity
                if proximity > 3:
                    reasons.append("Near to dock")

            # 5. Same item / item-group consolidation
            if self._bin_contains_item(b.id, item.id):
                score += 20
                reasons.append("Consolidation: same item already here")
            elif item_group_id and self._bin_contains_item_group(
                b.id, item_group_id, org_id
            ):
                score += 15
                reasons.append("Item group affinity")

            dist_from_worker = self._distance(self._position(b), worker_position)
            results.append(
                self._build_suggestion(
                    bin_location=b,
                    score=score,
                    reasons=reasons,
                    available_capacity=available,
                    distance_from_worker=dist_from_worker,
                )
            )

        return results

    # ------------------------------------------------------------------
    # PICK SCORING (section 7.2)
    # ------------------------------------------------------------------

    def _score_pick(
        self,
        item: Item,
        quantity: Decimal,
        warehouse_id: UUID,
        org_id: UUID,
        batch_number: str | None,
        reserved_bin_ids: set[UUID],
        excluded: set[UUID],
        worker_position: Position,
        max_distance: float,
    ) -> list[dict]:
        query = self.db.query(BinStockLevel).filter(
            BinStockLevel.item_id == item.id,
            BinStockLevel.organization_id == org_id,
            BinStockLevel.quantity_on_hand > 0,
        )
        if batch_number:
            query = query.filter(BinStockLevel.batch_number == batch_number)
        bin_stocks = query.all()

        today = datetime.now(UTC).date()
        results: list[dict] = []
        for bs in bin_stocks:
            if bs.bin_location_id in excluded or bs.bin_location_id in reserved_bin_ids:
                continue

            bin_location = (
                self.db.query(WarehouseLocation)
                .filter(
                    WarehouseLocation.id == bs.bin_location_id,
                    WarehouseLocation.warehouse_id == warehouse_id,
                    WarehouseLocation.is_active.is_(True),
                )
                .first()
            )
            if bin_location is None:
                continue

            reasons: list[str] = []
            score = 0.0

            # 1./2. FEFO then FIFO
            if bs.expiry_date is not None:
                days_until_expiry = (bs.expiry_date - today).days
                score += (365 - days_until_expiry) * 100
                reasons.append(f"FEFO: expires in {days_until_expiry} day(s)")
            else:
                created = bs.created_at.date() if bs.created_at else today
                age_days = (today - created).days
                score += age_days * 80
                reasons.append(f"FIFO: {age_days} day(s) in stock")

            # 3. Quantity match
            on_hand = Decimal(str(bs.quantity_on_hand or 0))
            if on_hand >= quantity:
                score += 20
                reasons.append("Satisfies full quantity in one stop")
            else:
                score += 5

            # 4. Route efficiency
            dist = self._distance(self._position(bin_location), worker_position)
            if max_distance > 0:
                route = (1 - min(dist / max_distance, 1.0)) * 30
                score += route

            results.append(
                self._build_suggestion(
                    bin_location=bin_location,
                    score=score,
                    reasons=reasons,
                    available_capacity=on_hand,
                    distance_from_worker=dist,
                    batch_number=bs.batch_number,
                    expiry_date=bs.expiry_date,
                )
            )

        return results

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _allocated_location_ids(
        self, org_id: UUID, item_group_id: UUID | None, allocation_type: str
    ) -> set[UUID]:
        """Return active bin ids allocated for a group (or all groups when None).

        Resolves allocations that point at non-bin levels down to descendant
        bins so allocation applies to the whole sub-tree.
        """
        query = self.db.query(LocationAllocation).filter(
            LocationAllocation.organization_id == org_id,
            LocationAllocation.allocation_type == allocation_type,
            LocationAllocation.is_active.is_(True),
        )
        if item_group_id is not None:
            query = query.filter(LocationAllocation.item_group_id == item_group_id)

        bin_ids: set[UUID] = set()
        for alloc in query.all():
            loc = (
                self.db.query(WarehouseLocation)
                .filter(
                    WarehouseLocation.id == alloc.location_id,
                    WarehouseLocation.is_active.is_(True),
                )
                .first()
            )
            if loc is None:
                continue
            if loc.location_type == "bin":
                bin_ids.add(loc.id)
            else:
                bin_ids.update(self._descendant_bin_ids(loc.id))
        return bin_ids

    def _descendant_bin_ids(self, location_id: UUID) -> set[UUID]:
        bin_ids: set[UUID] = set()
        queue = [location_id]
        while queue:
            current = queue.pop(0)
            children = (
                self.db.query(WarehouseLocation)
                .filter(
                    WarehouseLocation.parent_location_id == current,
                    WarehouseLocation.is_active.is_(True),
                )
                .all()
            )
            for child in children:
                if child.location_type == "bin":
                    bin_ids.add(child.id)
                else:
                    queue.append(child.id)
        return bin_ids

    def _available_capacity(self, bin_location: WarehouseLocation) -> Decimal:
        bin_capacity = Decimal(str(bin_location.capacity or 0))
        current = (
            self.db.query(
                func.coalesce(func.sum(BinStockLevel.quantity_on_hand), Decimal("0"))
            )
            .filter(BinStockLevel.bin_location_id == bin_location.id)
            .scalar()
        ) or Decimal("0")
        return bin_capacity - Decimal(str(current))

    def _bin_contains_item(self, bin_id: UUID, item_id: UUID) -> bool:
        return (
            self.db.query(BinStockLevel.id)
            .filter(
                BinStockLevel.bin_location_id == bin_id,
                BinStockLevel.item_id == item_id,
                BinStockLevel.quantity_on_hand > 0,
            )
            .first()
            is not None
        )

    def _bin_contains_item_group(
        self, bin_id: UUID, item_group_id: UUID, org_id: UUID
    ) -> bool:
        return (
            self.db.query(BinStockLevel.id)
            .join(Item, BinStockLevel.item_id == Item.id)
            .filter(
                BinStockLevel.bin_location_id == bin_id,
                BinStockLevel.quantity_on_hand > 0,
                Item.item_group_id == item_group_id,
                Item.organization_id == org_id,
            )
            .first()
            is not None
        )

    def _get_dock_position(self, warehouse_id: UUID, org_id: UUID) -> Position:
        """Dock door position from the floor plan, defaulting to origin.

        The warehouse_floor_plans table (Phase 0) is not guaranteed to exist
        yet, so this falls back to the origin if unavailable.
        """
        try:
            row = self.db.execute(
                _floor_plan_dock_query(), {"wid": str(warehouse_id)}
            ).first()
        except Exception:
            # Floor plan table may not exist yet (Phase 0). Roll back the failed
            # statement so the surrounding session stays usable.
            self.db.rollback()
            row = None
        if row and row[0]:
            docks = row[0]
            if isinstance(docks, list) and docks:
                d = docks[0]
                return (
                    float(d.get("x", 0)),
                    float(d.get("y", 0)),
                    0.0,
                )
        return (0.0, 0.0, 0.0)

    def _get_max_distance(self, warehouse_id: UUID, org_id: UUID) -> float:
        """Diagonal extent of bin positions; used to normalise distances."""
        row = (
            self.db.query(
                func.max(WarehouseLocation.position_x),
                func.max(WarehouseLocation.position_y),
                func.max(WarehouseLocation.position_z),
            )
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
            )
            .first()
        )
        if not row or row[0] is None:
            return 1.0
        mx = float(row[0] or 0)
        my = float(row[1] or 0)
        mz = float(row[2] or 0)
        diag = math.sqrt(mx * mx + my * my + mz * mz)
        return diag if diag > 0 else 1.0

    @staticmethod
    def _position(bin_location: WarehouseLocation) -> Position:
        return (
            float(bin_location.position_x or 0),
            float(bin_location.position_y or 0),
            float(bin_location.position_z or 0),
        )

    @staticmethod
    def _distance(a: Position, b: Position) -> float:
        return math.sqrt(
            (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2
        )

    @staticmethod
    def _build_suggestion(
        bin_location: WarehouseLocation,
        score: float,
        reasons: list[str],
        available_capacity: Decimal,
        distance_from_worker: float,
        batch_number: str | None = None,
        expiry_date: date | None = None,
    ) -> dict:
        # Rough estimate: 1 metre/second walking + 5s handling.
        estimated_time = int(distance_from_worker + 5)
        return {
            "bin_id": bin_location.id,
            "bin_code": bin_location.full_path,
            "position": {
                "x": float(bin_location.position_x or 0),
                "y": float(bin_location.position_y or 0),
                "z": float(bin_location.position_z or 0),
            },
            "score": round(score, 2),
            "reasons": reasons,
            "available_capacity": float(available_capacity),
            "distance_from_worker": round(distance_from_worker, 2),
            "estimated_time_seconds": estimated_time,
            "batch_number": batch_number,
            "expiry_date": expiry_date.isoformat() if expiry_date else None,
        }


def _floor_plan_dock_query():
    """Raw SQL selecting dock_doors JSON from warehouse_floor_plans by id.

    Isolated so the import-time dependency on the (possibly absent) table is
    deferred until a suggestion is actually requested.
    """
    from sqlalchemy import text

    return text(
        "SELECT dock_doors FROM warehouse_floor_plans "
        "WHERE warehouse_id = :wid LIMIT 1"
    )
