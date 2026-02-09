"""Stock entries and items API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.common import PaginationMeta
from app.schemas.stock_entry import (
    StockEntryCreate,
    StockEntryItemCreate,
    StockEntryItemResponse,
    StockEntryItemUpdate,
    StockEntryListItem,
    StockEntryListResponse,
    StockEntryResponse,
    StockEntryUpdate,
)
from app.services.stock_entry_service import StockEntryService

router = APIRouter()


@router.post("", response_model=StockEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_entry(
    data: StockEntryCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a stock entry with optional line items."""
    svc = StockEntryService(db)
    e = svc.create(data, current_user.organization_id, current_user.id)
    return StockEntryResponse.model_validate(e)


@router.get("", response_model=StockEntryListResponse)
async def list_stock_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    stock_entry_type: str | None = Query(None),
    status: str | None = Query(None),
    from_warehouse_id: UUID | None = None,
    to_warehouse_id: UUID | None = None,
    search: str | None = None,
    sort_by: str = Query("posting_date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List stock entries with filters."""
    svc = StockEntryService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        stock_entry_type=stock_entry_type,
        status=status,
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return StockEntryListResponse(
        stock_entries=[StockEntryListItem.model_validate(e) for e in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{entry_id}", response_model=StockEntryResponse)
async def get_stock_entry(
    entry_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get stock entry by ID including line items."""
    svc = StockEntryService(db)
    e = svc.get_by_id(entry_id, current_user.organization_id)
    return StockEntryResponse.model_validate(e)


@router.put("/{entry_id}", response_model=StockEntryResponse)
async def update_stock_entry(
    entry_id: UUID,
    data: StockEntryUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update stock entry header (draft only)."""
    svc = StockEntryService(db)
    svc.update(entry_id, data, current_user.organization_id, current_user.id)
    return StockEntryResponse.model_validate(
        svc.get_by_id(entry_id, current_user.organization_id)
    )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock_entry(
    entry_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a draft stock entry."""
    StockEntryService(db).delete(entry_id, current_user.organization_id)
    return None


# ----- Items (sub-resource) -----


@router.post(
    "/{entry_id}/items",
    response_model=StockEntryItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_stock_entry_item(
    entry_id: UUID,
    data: StockEntryItemCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add a line item to a draft stock entry."""
    svc = StockEntryService(db)
    it = svc.add_item(entry_id, data, current_user.organization_id)
    return StockEntryItemResponse.model_validate(it)


@router.put("/{entry_id}/items/{item_id}", response_model=StockEntryItemResponse)
async def update_stock_entry_item(
    entry_id: UUID,
    item_id: UUID,
    data: StockEntryItemUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a line item in a draft stock entry."""
    svc = StockEntryService(db)
    it = svc.update_item(entry_id, item_id, data, current_user.organization_id)
    return StockEntryItemResponse.model_validate(it)


@router.delete("/{entry_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock_entry_item(
    entry_id: UUID,
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Remove a line item from a draft stock entry."""
    StockEntryService(db).delete_item(entry_id, item_id, current_user.organization_id)
    return None
