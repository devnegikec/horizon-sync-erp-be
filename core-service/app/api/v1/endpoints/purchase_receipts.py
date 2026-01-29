"""Purchase receipts API endpoints (Phase 5)"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    PURCHASE_RECEIPT_CREATE,
    PURCHASE_RECEIPT_READ,
    PURCHASE_RECEIPT_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.purchase_receipt import (
    PurchaseReceiptCreate,
    PurchaseReceiptListItem,
    PurchaseReceiptListResponse,
    PurchaseReceiptResponse,
    PurchaseReceiptUpdate,
)
from app.services.purchase_receipt_service import PurchaseReceiptService

router = APIRouter()


@router.post(
    "", response_model=PurchaseReceiptResponse, status_code=status.HTTP_201_CREATED
)
async def create_purchase_receipt(
    body: PurchaseReceiptCreate,
    current_user: CurrentUser = Depends(require_permission(PURCHASE_RECEIPT_CREATE)),
    db: Session = Depends(get_db),
):
    """Create purchase receipt. Requires purchase_receipt.create."""
    svc = PurchaseReceiptService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)
    return PurchaseReceiptResponse.model_validate(data)


@router.get("", response_model=PurchaseReceiptListResponse)
async def list_purchase_receipts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    supplier_id: UUID | None = None,
    status: str | None = Query(None, pattern="^(draft|submitted|cancelled)$"),
    sort_by: str = Query("receipt_date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(require_permission(PURCHASE_RECEIPT_READ)),
    db: Session = Depends(get_db),
):
    """List purchase receipts. Requires purchase_receipt.read."""
    svc = PurchaseReceiptService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        supplier_id=supplier_id,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PurchaseReceiptListResponse(
        purchase_receipts=[PurchaseReceiptListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{purchase_receipt_id}", response_model=PurchaseReceiptResponse)
async def get_purchase_receipt(
    purchase_receipt_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PURCHASE_RECEIPT_READ)),
    db: Session = Depends(get_db),
):
    """Get purchase receipt by ID. Requires purchase_receipt.read."""
    svc = PurchaseReceiptService(db)
    data = svc.get_by_id(purchase_receipt_id, current_user.organization_id)
    return PurchaseReceiptResponse.model_validate(data)


@router.put("/{purchase_receipt_id}", response_model=PurchaseReceiptResponse)
async def update_purchase_receipt(
    purchase_receipt_id: UUID,
    body: PurchaseReceiptUpdate,
    current_user: CurrentUser = Depends(require_permission(PURCHASE_RECEIPT_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update purchase receipt. Requires purchase_receipt.update."""
    svc = PurchaseReceiptService(db)
    data = svc.update(
        purchase_receipt_id,
        body.model_dump(exclude_unset=True),
        current_user.organization_id,
        current_user.id,
    )
    return PurchaseReceiptResponse.model_validate(data)


@router.delete("/{purchase_receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_receipt(
    purchase_receipt_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PURCHASE_RECEIPT_UPDATE)),
    db: Session = Depends(get_db),
):
    """Delete purchase receipt. Requires purchase_receipt.update."""
    svc = PurchaseReceiptService(db)
    svc.delete(purchase_receipt_id, current_user.organization_id)
    return None
