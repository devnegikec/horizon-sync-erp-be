"""Floor Plan Designer API endpoints.

Exposes:
- POST /floor-plans/preview   — dry-run: compute positions, return summary
- POST /floor-plans/apply     — generate + persist locations + floor plan record
- GET  /floor-plans           — list floor plans for a warehouse
- GET  /floor-plans/{id}      — get single floor plan

Design ref: docs/3D_WAREHOUSE_VIEW_DESIGN.md section 2.1
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.authorization import WAREHOUSE_CREATE, WAREHOUSE_MANAGE, WAREHOUSE_READ
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models.warehouse_floor_plan import WarehouseFloorPlan
from app.schemas.floor_plan import (
    FloorPlanApplyRequest,
    FloorPlanApplyResponse,
    FloorPlanPreviewRequest,
    FloorPlanPreviewResponse,
    FloorPlanResponse,
    FloorPlanUpdateRequest,
    FloorPlanUpdateResponse,
    FloorPlanDeleteResponse,
)
from app.services.floor_plan_generator_service import FloorPlanGeneratorService

router = APIRouter()


@router.post("/preview", response_model=FloorPlanPreviewResponse, summary="Preview layout")
async def preview_floor_plan(
    body: FloorPlanPreviewRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Dry-run — compute bin positions and return a summary without writing to DB."""
    service = FloorPlanGeneratorService(db)
    return service.preview(
        warehouse_id=body.warehouse_id,
        org_id=current_user.organization_id,
        config=body.config,
    )


@router.post("/apply", response_model=FloorPlanApplyResponse, summary="Apply layout")
async def apply_floor_plan(
    body: FloorPlanApplyRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_MANAGE)),
    db: Session = Depends(get_db),
):
    """Generate bin hierarchy from config and persist to DB.

    Set replace_existing=true to deactivate all current locations for this
    warehouse before inserting the new ones.  The old locations are soft-deleted
    (is_active=false) so historical stock data is preserved.
    """
    service = FloorPlanGeneratorService(db)
    return service.apply(
        warehouse_id=body.warehouse_id,
        org_id=current_user.organization_id,
        config=body.config,
        name=body.name,
        description=body.description,
        replace_existing=body.replace_existing,
    )


@router.get("", response_model=list[FloorPlanResponse], summary="List floor plans")
async def list_floor_plans(
    warehouse_id: UUID = Query(...),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """List all floor plans for a warehouse, newest first."""
    rows = (
        db.query(WarehouseFloorPlan)
        .filter(
            WarehouseFloorPlan.warehouse_id == warehouse_id,
            WarehouseFloorPlan.organization_id == current_user.organization_id,
        )
        .order_by(WarehouseFloorPlan.created_at.desc())
        .all()
    )
    return [_to_response(r) for r in rows]


@router.get("/{floor_plan_id}", response_model=FloorPlanResponse, summary="Get floor plan")
async def get_floor_plan(
    floor_plan_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Retrieve a single floor plan by ID."""
    row = (
        db.query(WarehouseFloorPlan)
        .filter(
            WarehouseFloorPlan.id == floor_plan_id,
            WarehouseFloorPlan.organization_id == current_user.organization_id,
        )
        .first()
    )
    if row is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found")
    return _to_response(row)


@router.post("/seed-templates", summary="Seed layout templates for a warehouse")
async def seed_templates(
    warehouse_id: UUID = Query(...),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_MANAGE)),
    db: Session = Depends(get_db),
):
    """Seed preloaded layout templates for an existing warehouse.

    Idempotent — templates that already exist are skipped.
    Templates are saved as inactive and won't generate locations until applied.
    """
    service = FloorPlanGeneratorService(db)
    count = service.seed_templates(warehouse_id, current_user.organization_id)
    db.commit()
    return {"seeded": count, "warehouse_id": warehouse_id}


@router.post("/reset", summary="Reset warehouse layout (delete all plans + locations)")
async def reset_warehouse_layout(
    warehouse_id: UUID = Query(...),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_MANAGE)),
    db: Session = Depends(get_db),
):
    """Delete ALL floor plans and locations for a warehouse.

    This is a destructive action — use to start fresh.
    Active pick and put-away work is cancelled first, then locations are
    soft-deactivated and their bin stock is cleared so no stale location data
    remains for future assignment.
    Floor plan records are hard-deleted.
    """
    from datetime import UTC, datetime
    from collections import defaultdict

    from app.models.pick_list import PickList
    from app.models.put_away_list import PutAwayList
    from app.models.base import PickListStatus
    from app.models.bin_reservation import BinReservation
    from app.models.stock_level import StockLevel
    from app.services.pick_list_service import PickListService

    # Delete all floor plans for this warehouse
    plans_deleted = (
        db.query(WarehouseFloorPlan)
        .filter(
            WarehouseFloorPlan.warehouse_id == warehouse_id,
            WarehouseFloorPlan.organization_id == current_user.organization_id,
        )
        .delete(synchronize_session='fetch')
    )

    # Cancel active pick work so no pick items keep pointing at bin stock that
    # is about to be cleared. Performed inline within this endpoint's single
    # transaction (one commit at the end) so a failure can't leave the reset
    # partially applied.
    active_pick_statuses = [
        PickListStatus.DRAFT.value,
        PickListStatus.CONFIRMED.value,
        PickListStatus.PENDING_PICKING.value,
        PickListStatus.IN_PROGRESS.value,
    ]
    active_pick_lists = (
        db.query(PickList)
        .filter(
            PickList.warehouse_id == warehouse_id,
            PickList.organization_id == current_user.organization_id,
            PickList.status.in_(active_pick_statuses),
        )
        .all()
    )
    pick_list_ids = [pl.id for pl in active_pick_lists]
    for pl in active_pick_lists:
        pl.status = PickListStatus.CANCELLED

    if pick_list_ids:
        # Release the pick lists' bin reservations (released_at preserves the
        # audit trail instead of deleting rows).
        db.query(BinReservation).filter(
            BinReservation.organization_id == current_user.organization_id,
            BinReservation.task_id.in_(pick_list_ids),
            BinReservation.released_at.is_(None),
        ).update({"released_at": datetime.now(UTC)}, synchronize_session=False)

        # Release warehouse-level stock reservations held by order-driven lists.
        release_qty: dict[tuple[UUID, UUID], int] = defaultdict(int)
        for pl in active_pick_lists:
            if pl.reference_type != "outbound_order":
                continue
            for item in pl.items:
                release_qty[(item.item_id, item.warehouse_id)] += int(item.qty or 0)
        for (item_id, wh_id), qty in release_qty.items():
            stock = (
                db.query(StockLevel)
                .filter(
                    StockLevel.organization_id == current_user.organization_id,
                    StockLevel.product_id == item_id,
                    StockLevel.warehouse_id == wh_id,
                )
                .first()
            )
            if stock is not None:
                stock.quantity_reserved = max(
                    0, (stock.quantity_reserved or 0) - qty
                )
                stock.quantity_available = max(
                    0,
                    (stock.quantity_on_hand or 0) - (stock.quantity_reserved or 0),
                )

    db.flush()

    # Revert affected orders back to confirmed so they can be re-picked.
    pick_service = PickListService(db)
    for order_id in {
        pl.reference_id
        for pl in active_pick_lists
        if pl.reference_type == "outbound_order" and pl.reference_id
    }:
        pick_service._revert_order_if_all_cancelled(
            order_id, current_user.organization_id
        )

    # Cancel active put-away lists for the same reason.
    putaway_cancelled = (
        db.query(PutAwayList)
        .filter(
            PutAwayList.warehouse_id == warehouse_id,
            PutAwayList.organization_id == current_user.organization_id,
            PutAwayList.status != "completed",
        )
        .update({"status": "cancelled"}, synchronize_session="fetch")
    )

    # Soft-deactivate all pickable locations and clear their bin stock so
    # nothing stale survives.
    service = FloorPlanGeneratorService(db)
    locations_removed = service._deactivate_existing(
        warehouse_id, current_user.organization_id, clear_stock=True
    )

    db.commit()
    return {
        "warehouse_id": warehouse_id,
        "plans_deleted": plans_deleted,
        "locations_removed": locations_removed,
        "pick_lists_cancelled": len(active_pick_lists),
        "put_away_lists_cancelled": putaway_cancelled,
    }


@router.put(
    "/{floor_plan_id}",
    response_model=FloorPlanUpdateResponse,
    summary="Update floor plan",
)
async def update_floor_plan(
    floor_plan_id: UUID,
    body: FloorPlanUpdateRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_MANAGE)),
    db: Session = Depends(get_db),
):
    """Update an existing floor plan's config and re-generate locations.

    This deactivates the locations created by the previous version of this plan,
    then generates new locations from the updated config.  The floor plan record
    itself is updated in-place (same ID).
    """
    service = FloorPlanGeneratorService(db)
    return service.update(
        floor_plan_id=floor_plan_id,
        org_id=current_user.organization_id,
        config=body.config,
        name=body.name,
        description=body.description,
    )


@router.delete(
    "/{floor_plan_id}",
    response_model=FloorPlanDeleteResponse,
    summary="Delete floor plan",
)
async def delete_floor_plan(
    floor_plan_id: UUID,
    deactivate_locations: bool = Query(
        False,
        description="Also deactivate warehouse locations generated by this plan",
    ),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_MANAGE)),
    db: Session = Depends(get_db),
):
    """Soft-delete a floor plan.  Optionally deactivate its generated locations."""
    service = FloorPlanGeneratorService(db)
    return service.delete(
        floor_plan_id=floor_plan_id,
        org_id=current_user.organization_id,
        deactivate_locations=deactivate_locations,
    )


def _to_response(row: WarehouseFloorPlan) -> FloorPlanResponse:
    from app.schemas.floor_plan import FloorPlanConfig
    return FloorPlanResponse(
        id=row.id,
        warehouse_id=row.warehouse_id,
        name=row.name,
        description=row.description,
        config=FloorPlanConfig.model_validate(row.config),
        generated_at=row.generated_at.isoformat() if row.generated_at else None,
        is_active=row.is_active,
        created_at=row.created_at.isoformat(),
    )
