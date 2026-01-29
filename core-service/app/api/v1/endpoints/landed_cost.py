"""Landed cost vouchers API endpoints (Phase 6)"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    LANDED_COST_CREATE,
    LANDED_COST_READ,
    LANDED_COST_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.landed_cost import (
    LandedCostVoucherCreate,
    LandedCostVoucherListItem,
    LandedCostVoucherListResponse,
    LandedCostVoucherResponse,
    LandedCostVoucherUpdate,
)
from app.services.landed_cost_service import LandedCostService

router = APIRouter()


@router.post(
    "", response_model=LandedCostVoucherResponse, status_code=status.HTTP_201_CREATED
)
async def create_landed_cost_voucher(
    body: LandedCostVoucherCreate,
    current_user: CurrentUser = Depends(require_permission(LANDED_COST_CREATE)),
    db: Session = Depends(get_db),
):
    """Create landed cost voucher. Requires landed_cost.create."""
    svc = LandedCostService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)
    return LandedCostVoucherResponse.model_validate(data)


@router.get("", response_model=LandedCostVoucherListResponse)
async def list_landed_cost_vouchers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, pattern="^(draft|submitted|cancelled)$"),
    sort_by: str = Query("posting_date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(require_permission(LANDED_COST_READ)),
    db: Session = Depends(get_db),
):
    """List landed cost vouchers. Requires landed_cost.read."""
    svc = LandedCostService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return LandedCostVoucherListResponse(
        vouchers=[LandedCostVoucherListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{voucher_id}", response_model=LandedCostVoucherResponse)
async def get_landed_cost_voucher(
    voucher_id: UUID,
    current_user: CurrentUser = Depends(require_permission(LANDED_COST_READ)),
    db: Session = Depends(get_db),
):
    """Get landed cost voucher by ID. Requires landed_cost.read."""
    svc = LandedCostService(db)
    data = svc.get_by_id(voucher_id, current_user.organization_id)
    return LandedCostVoucherResponse.model_validate(data)


@router.put("/{voucher_id}", response_model=LandedCostVoucherResponse)
async def update_landed_cost_voucher(
    voucher_id: UUID,
    body: LandedCostVoucherUpdate,
    current_user: CurrentUser = Depends(require_permission(LANDED_COST_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update landed cost voucher. Requires landed_cost.update."""
    svc = LandedCostService(db)
    data = svc.update(
        voucher_id,
        body.model_dump(exclude_unset=True),
        current_user.organization_id,
        current_user.id,
    )
    return LandedCostVoucherResponse.model_validate(data)


@router.delete("/{voucher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_landed_cost_voucher(
    voucher_id: UUID,
    current_user: CurrentUser = Depends(require_permission(LANDED_COST_UPDATE)),
    db: Session = Depends(get_db),
):
    """Delete landed cost voucher. Requires landed_cost.update."""
    svc = LandedCostService(db)
    svc.delete(voucher_id, current_user.organization_id)
    return None
