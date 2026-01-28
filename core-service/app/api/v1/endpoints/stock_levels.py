"""Stock levels API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.common import PaginationMeta
from app.schemas.stock_level import (
    StockLevelCreate,
    StockLevelListItem,
    StockLevelListResponse,
    StockLevelResponse,
    StockLevelUpdate,
)
from app.services.stock_level_service import StockLevelService

router = APIRouter()


@router.post("", response_model=StockLevelResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_level(
    data: StockLevelCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create or upsert a stock level for an item in a warehouse."""
    svc = StockLevelService(db)
    s = svc.create(data, current_user.organization_id)
    return StockLevelResponse.model_validate(s)


@router.get("", response_model=StockLevelListResponse)
async def list_stock_levels(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_id: UUID | None = Query(None, description="Filter by item (product) ID"),
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse ID"),
    sort_by: str = Query("updated_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List stock levels with filters."""
    svc = StockLevelService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        product_id=item_id,
        warehouse_id=warehouse_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return StockLevelListResponse(
        stock_levels=[StockLevelListItem.model_validate(s) for s in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/by-location", response_model=StockLevelResponse)
async def get_stock_level_by_location(
    item_id: UUID = Query(..., description="Item (product) ID"),
    warehouse_id: UUID = Query(..., description="Warehouse ID"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get stock level for an item in a warehouse. 404 if not found."""
    svc = StockLevelService(db)
    s = svc.get(item_id, warehouse_id, current_user.organization_id)
    return StockLevelResponse.model_validate(s)


@router.get("/{level_id}", response_model=StockLevelResponse)
async def get_stock_level(
    level_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get stock level by ID."""
    svc = StockLevelService(db)
    return StockLevelResponse.model_validate(
        svc.get_by_id(level_id, current_user.organization_id)
    )


@router.put("/by-location", response_model=StockLevelResponse)
async def update_stock_level_by_location(
    item_id: UUID = Query(...),
    warehouse_id: UUID = Query(...),
    data: StockLevelUpdate = ...,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update stock level for an item in a warehouse."""
    svc = StockLevelService(db)
    s = svc.update(item_id, warehouse_id, data, current_user.organization_id)
    return StockLevelResponse.model_validate(s)


@router.put("/{level_id}", response_model=StockLevelResponse)
async def update_stock_level(
    level_id: UUID,
    data: StockLevelUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update stock level by ID."""
    svc = StockLevelService(db)
    s = svc.update_by_id(level_id, data, current_user.organization_id)
    return StockLevelResponse.model_validate(s)
