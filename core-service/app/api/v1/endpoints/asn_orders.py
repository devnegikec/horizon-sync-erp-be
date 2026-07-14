"""ASN Orders API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    ASN_ORDER_CREATE,
    ASN_ORDER_READ,
    ASN_ORDER_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.asn_order import (
    AsnOrderCreate,
    AsnOrderListItem,
    AsnOrderListResponse,
    AsnOrderResponse,
    AsnOrderStatusUpdate,
    AsnOrderUpdate,
)
from app.schemas.common import PaginationMeta
from app.services.asn_order_service import AsnOrderService

router = APIRouter()


@router.post("", response_model=AsnOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_asn_order(
    body: AsnOrderCreate,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_CREATE)),
    db: Session = Depends(get_db),
):
    """Create ASN order. Requires asn_order.create."""
    svc = AsnOrderService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)
    return AsnOrderResponse.model_validate(data)


@router.get("", response_model=AsnOrderListResponse)
async def list_asn_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(
        None,
        pattern="^(draft|confirmed|partially_delivered|delivered|closed|cancelled)$",
    ),
    warehouse_id: UUID | None = Query(None, description="Filter where from OR to warehouse matches"),
    search: str | None = Query(None, description="Search by ASN order number"),
    sort_by: str = Query("order_date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """List ASN orders. Requires asn_order.read."""
    svc = AsnOrderService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        status=status,
        warehouse_id=warehouse_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return AsnOrderListResponse(
        asn_orders=[AsnOrderListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{asn_order_id}", response_model=AsnOrderResponse)
async def get_asn_order(
    asn_order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """Get ASN order by ID. Requires asn_order.read."""
    svc = AsnOrderService(db)
    data = svc.get_by_id(asn_order_id, current_user.organization_id)
    return AsnOrderResponse.model_validate(data)


@router.put("/{asn_order_id}", response_model=AsnOrderResponse)
async def update_asn_order(
    asn_order_id: UUID,
    body: AsnOrderUpdate,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update ASN order. Requires asn_order.update."""
    svc = AsnOrderService(db)
    data = svc.update(
        asn_order_id,
        body.model_dump(exclude_unset=True),
        current_user.organization_id,
        current_user.id,
    )
    return AsnOrderResponse.model_validate(data)


@router.delete("/{asn_order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asn_order(
    asn_order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Delete ASN order. Requires asn_order.update."""
    svc = AsnOrderService(db)
    svc.delete(asn_order_id, current_user.organization_id)
    return None


@router.put("/{asn_order_id}/status", response_model=AsnOrderResponse)
async def update_asn_order_status(
    asn_order_id: UUID,
    body: AsnOrderStatusUpdate,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update ASN order status. Requires asn_order.update."""
    svc = AsnOrderService(db)
    data = svc.update_status(
        asn_order_id,
        body.status,
        current_user.organization_id,
        current_user.id,
    )
    return AsnOrderResponse.model_validate(data)
