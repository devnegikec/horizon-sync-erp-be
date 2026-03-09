"""Sales Orders API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    SALES_ORDER_CREATE,
    SALES_ORDER_READ,
    SALES_ORDER_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.sales_order import (
    ConvertToDeliveryNoteRequest,
    ConvertToDeliveryNoteResponse,
    ConvertToInvoiceRequest,
    ConvertToInvoiceResponse,
    SalesOrderCreate,
    SalesOrderListItem,
    SalesOrderListResponse,
    SalesOrderResponse,
    SalesOrderStatusUpdate,
    SalesOrderUpdate,
)
from app.services.sales_order_service import SalesOrderService

router = APIRouter()


@router.post("", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_sales_order(
    body: SalesOrderCreate,
    current_user: CurrentUser = Depends(require_permission(SALES_ORDER_CREATE)),
    db: Session = Depends(get_db),
):
    """Create sales order. Requires sales_order.create."""
    svc = SalesOrderService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)
    return SalesOrderResponse.model_validate(data)


@router.get("", response_model=SalesOrderListResponse)
async def list_sales_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: UUID | None = None,
    status: str | None = Query(
        None,
        pattern="^(draft|confirmed|partially_delivered|delivered|closed|cancelled)$",
    ),
    sort_by: str = Query("order_date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(require_permission(SALES_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """List sales orders. Requires sales_order.read."""
    svc = SalesOrderService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return SalesOrderListResponse(
        sales_orders=[SalesOrderListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{sales_order_id}", response_model=SalesOrderResponse)
async def get_sales_order(
    sales_order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(SALES_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """Get sales order by ID. Requires sales_order.read."""
    svc = SalesOrderService(db)
    data = svc.get_by_id(sales_order_id, current_user.organization_id)
    return SalesOrderResponse.model_validate(data)


@router.put("/{sales_order_id}", response_model=SalesOrderResponse)
async def update_sales_order(
    sales_order_id: UUID,
    body: SalesOrderUpdate,
    current_user: CurrentUser = Depends(require_permission(SALES_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update sales order. Requires sales_order.update."""
    svc = SalesOrderService(db)
    data = svc.update(
        sales_order_id,
        body.model_dump(exclude_unset=True),
        current_user.organization_id,
        current_user.id,
    )
    return SalesOrderResponse.model_validate(data)


@router.delete("/{sales_order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sales_order(
    sales_order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(SALES_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Delete sales order. Requires sales_order.update."""
    svc = SalesOrderService(db)
    svc.delete(sales_order_id, current_user.organization_id)
    return None


@router.put("/{sales_order_id}/status", response_model=SalesOrderResponse)
async def update_sales_order_status(
    sales_order_id: UUID,
    body: SalesOrderStatusUpdate,
    current_user: CurrentUser = Depends(require_permission(SALES_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update sales order status. Requires sales_order.update."""
    svc = SalesOrderService(db)
    data = svc.update_status(
        sales_order_id,
        body.status,
        current_user.organization_id,
        current_user.id,
    )
    return SalesOrderResponse.model_validate(data)


@router.post(
    "/{sales_order_id}/convert-to-invoice",
    response_model=ConvertToInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def convert_sales_order_to_invoice(
    sales_order_id: UUID,
    body: ConvertToInvoiceRequest,
    current_user: CurrentUser = Depends(require_permission(SALES_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Convert sales order to invoice. Requires sales_order.update."""
    svc = SalesOrderService(db)
    invoice = svc.convert_to_invoice(
        sales_order_id,
        [item.model_dump() for item in body.items],
        current_user.organization_id,
        current_user.id,
    )
    return ConvertToInvoiceResponse(
        invoice_id=invoice["id"],
        invoice_no=invoice["invoice_no"],
    )


@router.post(
    "/{sales_order_id}/convert-to-delivery-note",
    response_model=ConvertToDeliveryNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def convert_sales_order_to_delivery_note(
    sales_order_id: UUID,
    body: ConvertToDeliveryNoteRequest,
    current_user: CurrentUser = Depends(require_permission(SALES_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Convert sales order to delivery note. Requires sales_order.update."""
    svc = SalesOrderService(db)
    delivery_note = svc.convert_to_delivery_note(
        sales_order_id,
        [item.model_dump() for item in body.items],
        current_user.organization_id,
        current_user.id,
    )
    return ConvertToDeliveryNoteResponse(
        delivery_note_id=delivery_note["id"],
        delivery_note_no=delivery_note["delivery_note_no"],
    )
