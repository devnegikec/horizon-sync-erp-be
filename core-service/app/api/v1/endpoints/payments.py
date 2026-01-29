"""Payments API endpoints (Phase 7)"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import PAYMENT_CREATE, PAYMENT_READ
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.payment import (
    PaymentCreate,
    PaymentListItem,
    PaymentListResponse,
    PaymentResponse,
    PaymentUpdate,
)
from app.services.payment_service import PaymentService

router = APIRouter()


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    body: PaymentCreate,
    current_user: CurrentUser = Depends(require_permission(PAYMENT_CREATE)),
    db: Session = Depends(get_db),
):
    """Create payment. Requires payment.create."""
    svc = PaymentService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)
    return PaymentResponse.model_validate(data)


@router.get("", response_model=PaymentListResponse)
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    party_id: UUID | None = None,
    status: str | None = Query(None, pattern="^(pending|completed|failed|cancelled)$"),
    payment_type: str | None = Query(None, pattern="^(receive|pay)$"),
    sort_by: str = Query("posting_date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(require_permission(PAYMENT_READ)),
    db: Session = Depends(get_db),
):
    """List payments. Requires payment.read."""
    svc = PaymentService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        party_id=party_id,
        status=status,
        payment_type=payment_type,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PaymentListResponse(
        payments=[PaymentListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PAYMENT_READ)),
    db: Session = Depends(get_db),
):
    """Get payment by ID. Requires payment.read."""
    svc = PaymentService(db)
    data = svc.get_by_id(payment_id, current_user.organization_id)
    return PaymentResponse.model_validate(data)


@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: UUID,
    body: PaymentUpdate,
    current_user: CurrentUser = Depends(require_permission(PAYMENT_CREATE)),
    db: Session = Depends(get_db),
):
    """Update payment. Requires payment.create (or add payment.update)."""
    svc = PaymentService(db)
    data = svc.update(
        payment_id,
        body.model_dump(exclude_unset=True),
        current_user.organization_id,
        current_user.id,
    )
    return PaymentResponse.model_validate(data)


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PAYMENT_CREATE)),
    db: Session = Depends(get_db),
):
    """Delete payment. Requires payment.create."""
    svc = PaymentService(db)
    svc.delete(payment_id, current_user.organization_id)
    return None
