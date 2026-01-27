"""Item price management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.common import PaginationMeta
from app.schemas.item_price import (
    ItemPriceCreate,
    ItemPriceListItem,
    ItemPriceListResponse,
    ItemPriceResponse,
    ItemPriceUpdate,
)
from app.services.item_price_service import ItemPriceService

router = APIRouter()


@router.post("", response_model=ItemPriceResponse, status_code=status.HTTP_201_CREATED)
async def create_item_price(
    data: ItemPriceCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new item price. Item must exist."""
    svc = ItemPriceService(db)
    return ItemPriceResponse.model_validate(
        svc.create(data, current_user.organization_id)
    )


@router.get("", response_model=ItemPriceListResponse)
async def list_item_prices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_id: UUID | None = Query(None, description="Filter by item ID"),
    price_list_id: UUID | None = Query(None, description="Filter by price list ID"),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List item prices with pagination and filters."""
    svc = ItemPriceService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        item_id=item_id,
        price_list_id=price_list_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ItemPriceListResponse(
        item_prices=[ItemPriceListItem.model_validate(p) for p in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{price_id}", response_model=ItemPriceResponse)
async def get_item_price(
    price_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get item price by ID."""
    svc = ItemPriceService(db)
    return ItemPriceResponse.model_validate(
        svc.get_by_id(price_id, current_user.organization_id)
    )


@router.put("/{price_id}", response_model=ItemPriceResponse)
async def update_item_price(
    price_id: UUID,
    data: ItemPriceUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update an item price."""
    svc = ItemPriceService(db)
    return ItemPriceResponse.model_validate(
        svc.update(price_id, data, current_user.organization_id)
    )


@router.delete("/{price_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item_price(
    price_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete an item price."""
    ItemPriceService(db).delete(price_id, current_user.organization_id)
    return None
