"""Stock reconciliations and items API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.common import PaginationMeta
from app.schemas.stock_reconciliation import (
    StockReconciliationCreate,
    StockReconciliationItemCreate,
    StockReconciliationItemResponse,
    StockReconciliationItemUpdate,
    StockReconciliationListItem,
    StockReconciliationListResponse,
    StockReconciliationResponse,
    StockReconciliationUpdate,
)
from app.services.stock_reconciliation_service import StockReconciliationService

router = APIRouter()


@router.post(
    "", response_model=StockReconciliationResponse, status_code=status.HTTP_201_CREATED
)
async def create_stock_reconciliation(
    data: StockReconciliationCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a stock reconciliation with optional line items."""
    svc = StockReconciliationService(db)
    r = svc.create(data, current_user.organization_id, current_user.id)
    return StockReconciliationResponse.model_validate(r)


@router.get("", response_model=StockReconciliationListResponse)
async def list_stock_reconciliations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    search: str | None = None,
    sort_by: str = Query("posting_date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List stock reconciliations with filters."""
    svc = StockReconciliationService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return StockReconciliationListResponse(
        stock_reconciliations=[
            StockReconciliationListItem.model_validate(r) for r in items
        ],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{rec_id}", response_model=StockReconciliationResponse)
async def get_stock_reconciliation(
    rec_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get stock reconciliation by ID including line items."""
    svc = StockReconciliationService(db)
    r = svc.get_by_id(rec_id, current_user.organization_id)
    return StockReconciliationResponse.model_validate(r)


@router.put("/{rec_id}", response_model=StockReconciliationResponse)
async def update_stock_reconciliation(
    rec_id: UUID,
    data: StockReconciliationUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update stock reconciliation header (draft only)."""
    svc = StockReconciliationService(db)
    svc.update(rec_id, data, current_user.organization_id, current_user.id)
    return StockReconciliationResponse.model_validate(
        svc.get_by_id(rec_id, current_user.organization_id)
    )


@router.delete("/{rec_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock_reconciliation(
    rec_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a draft stock reconciliation."""
    StockReconciliationService(db).delete(rec_id, current_user.organization_id)
    return None


# ----- Items (sub-resource) -----


@router.post(
    "/{rec_id}/items",
    response_model=StockReconciliationItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_stock_reconciliation_item(
    rec_id: UUID,
    data: StockReconciliationItemCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add a line item to a draft stock reconciliation."""
    svc = StockReconciliationService(db)
    it = svc.add_item(rec_id, data, current_user.organization_id)
    return StockReconciliationItemResponse.model_validate(it)


@router.put("/{rec_id}/items/{item_id}", response_model=StockReconciliationItemResponse)
async def update_stock_reconciliation_item(
    rec_id: UUID,
    item_id: UUID,
    data: StockReconciliationItemUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a line item in a draft stock reconciliation."""
    svc = StockReconciliationService(db)
    it = svc.update_item(rec_id, item_id, data, current_user.organization_id)
    return StockReconciliationItemResponse.model_validate(it)


@router.delete("/{rec_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock_reconciliation_item(
    rec_id: UUID,
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Remove a line item from a draft stock reconciliation."""
    StockReconciliationService(db).delete_item(
        rec_id, item_id, current_user.organization_id
    )
    return None
