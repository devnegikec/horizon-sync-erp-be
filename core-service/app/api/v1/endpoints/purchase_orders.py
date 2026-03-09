"""Purchase Order API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderListItem,
    PurchaseOrderListResponse,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
)
from app.services.purchase_order_service import PurchaseOrderService

router = APIRouter()

# Permission constants (to be defined in authorization module)
PURCHASE_ORDER_CREATE = "purchase_order.create"
PURCHASE_ORDER_READ = "purchase_order.read"
PURCHASE_ORDER_UPDATE = "purchase_order.update"


@router.post(
    "", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED
)
async def create_purchase_order(
    body: PurchaseOrderCreate,
    current_user: CurrentUser = Depends(require_permission(PURCHASE_ORDER_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Create new Purchase Order.

    Can be created from an RFQ or standalone.
    Automatically calculates totals using Transaction Engine.
    Requires purchase_order.create permission.
    """
    svc = PurchaseOrderService(db)

    # If rfq_id is provided, create from RFQ
    if body.rfq_id:
        data = svc.create_from_rfq(
            rfq_id=body.rfq_id,
            supplier_id=body.party_id,
            line_items=[item.model_dump() for item in body.line_items],
            tax_rate=body.tax_rate,
            discount_amount=body.discount_amount,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
        )
    else:
        # Create standalone Purchase Order
        data = svc.create(
            party_id=body.party_id,
            line_items=[item.model_dump() for item in body.line_items],
            tax_rate=body.tax_rate,
            discount_amount=body.discount_amount,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            rfq_id=None,
        )

    return PurchaseOrderResponse.model_validate(data)


@router.get("", response_model=PurchaseOrderListResponse)
async def list_purchase_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(
        None,
        pattern="^(DRAFT|SUBMITTED|PARTIALLY_RECEIVED|FULLY_RECEIVED|CLOSED|CANCELLED|draft|submitted|partially_received|fully_received|closed|cancelled)$",
    ),
    rfq_id: UUID | None = Query(None, description="Filter by RFQ ID"),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    search: str | None = Query(None, description="Search in Purchase Order details"),
    current_user: CurrentUser = Depends(require_permission(PURCHASE_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """
    List Purchase Orders with pagination.

    Supports filtering by status, rfq_id, sorting, and search.
    Requires purchase_order.read permission.
    """
    svc = PurchaseOrderService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        status=status.lower() if status else None,
        rfq_id=rfq_id,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
    )
    return PurchaseOrderListResponse(
        purchase_orders=[PurchaseOrderListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_purchase_order(
    po_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PURCHASE_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """
    Retrieve Purchase Order by ID.

    Returns complete Purchase Order details including line items.
    Requires purchase_order.read permission.
    """
    svc = PurchaseOrderService(db)
    data = svc.get_by_id(po_id, current_user.organization_id)
    return PurchaseOrderResponse.model_validate(data)


@router.put("/{po_id}", response_model=PurchaseOrderResponse)
async def update_purchase_order(
    po_id: UUID,
    body: PurchaseOrderUpdate,
    current_user: CurrentUser = Depends(require_permission(PURCHASE_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Update Purchase Order (DRAFT only).

    Only Purchase Orders in DRAFT status can be modified.
    Automatically recalculates totals using Transaction Engine.
    Requires purchase_order.update permission.
    """
    svc = PurchaseOrderService(db)
    update_data = body.model_dump(exclude_unset=True)

    # Convert line items to dict if present
    if "line_items" in update_data and update_data["line_items"]:
        update_data["line_items"] = [item.model_dump() for item in body.line_items]

    data = svc.update(
        po_id,
        update_data,
        current_user.organization_id,
        current_user.id,
    )
    return PurchaseOrderResponse.model_validate(data)


@router.delete("/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_order(
    po_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PURCHASE_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Delete Purchase Order (DRAFT only).

    Only Purchase Orders in DRAFT status can be deleted.
    Requires purchase_order.update permission.
    """
    svc = PurchaseOrderService(db)
    svc.delete(po_id, current_user.organization_id)
    return None


@router.post("/{po_id}/submit", response_model=PurchaseOrderResponse)
async def submit_purchase_order(
    po_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PURCHASE_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Submit Purchase Order.

    Changes status from DRAFT to SUBMITTED.
    Prevents further modifications after submission.
    Requires purchase_order.update permission.
    """
    svc = PurchaseOrderService(db)
    data = svc.submit(po_id, current_user.organization_id, current_user.id)
    return PurchaseOrderResponse.model_validate(data)


@router.post("/{po_id}/cancel", response_model=PurchaseOrderResponse)
async def cancel_purchase_order(
    po_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PURCHASE_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Cancel Purchase Order.

    Changes status to CANCELLED.
    Can be cancelled from DRAFT or SUBMITTED status.
    Requires purchase_order.update permission.
    """
    svc = PurchaseOrderService(db)
    data = svc.cancel(po_id, current_user.organization_id, current_user.id)
    return PurchaseOrderResponse.model_validate(data)


@router.post("/{po_id}/close", response_model=PurchaseOrderResponse)
async def close_purchase_order(
    po_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PURCHASE_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Close Purchase Order.

    Changes status to CLOSED.
    Can only be closed from FULLY_RECEIVED status.
    Requires purchase_order.update permission.
    """
    svc = PurchaseOrderService(db)
    data = svc.close(po_id, current_user.organization_id, current_user.id)
    return PurchaseOrderResponse.model_validate(data)
