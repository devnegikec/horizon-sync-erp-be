"""Smart Picking API endpoints — suggest allocation, create pick list, create
delivery note from pick list."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    DELIVERY_NOTE_CREATE,
    PICK_LIST_CREATE,
    PICK_LIST_READ,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.smart_picking import (
    AllocationSuggestionResponse,
    DeliveryNoteFromPickListRequest,
    DeliveryNoteFromPickListResponse,
    SmartPickListCreate,
    SmartPickListResponse,
)
from app.services.smart_picking_service import SmartPickingService

router = APIRouter()


@router.get(
    "/suggest-allocation/{sales_order_id}",
    response_model=AllocationSuggestionResponse,
)
async def suggest_allocation(
    sales_order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    """Suggest warehouse allocation for a sales order's items.

    For each SO line item, queries stock_levels ordered by quantity_available
    DESC and splits the required qty across warehouses when a single warehouse
    can't fulfil the full amount.

    Requires: pick_list.read
    """
    svc = SmartPickingService(db)
    data = svc.suggest_allocation(sales_order_id, current_user.organization_id)
    return AllocationSuggestionResponse(**data)


@router.post(
    "/create",
    response_model=SmartPickListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_smart_pick_list(
    body: SmartPickListCreate,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_CREATE)),
    db: Session = Depends(get_db),
):
    """Create a pick list from confirmed allocations and reserve stock.

    For each allocation line, increments quantity_reserved and decrements
    quantity_available in stock_levels.  All operations run inside a single
    DB transaction.

    Requires: pick_list.create
    """
    svc = SmartPickingService(db)
    allocations = [a.model_dump() for a in body.allocations]
    data = svc.create_pick_list(
        sales_order_id=body.sales_order_id,
        allocations=allocations,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        remarks=body.remarks,
    )
    return SmartPickListResponse(**data)


@router.post(
    "/delivery-from-pick-list",
    response_model=DeliveryNoteFromPickListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_delivery_from_pick_list(
    body: DeliveryNoteFromPickListRequest,
    current_user: CurrentUser = Depends(require_permission(DELIVERY_NOTE_CREATE)),
    db: Session = Depends(get_db),
):
    """Convert a pick list into a delivery note.

    Decrements quantity_on_hand and quantity_reserved in stock_levels, creates
    stock_movement audit records, marks the pick list as completed, and updates
    delivered_qty on the sales order items.

    Requires: delivery_note.create
    """
    svc = SmartPickingService(db)
    data = svc.create_delivery_from_pick_list(
        pick_list_id=body.pick_list_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        delivery_date=body.delivery_date,
        remarks=body.remarks,
    )
    return DeliveryNoteFromPickListResponse(**data)
