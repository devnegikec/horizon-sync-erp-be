"""Item Price management API endpoints"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.common import PaginationMeta
from app.schemas.item_price import (
    ItemPriceBulkCreate,
    ItemPriceBulkResponse,
    ItemPriceCreate,
    ItemPriceListItem,
    ItemPriceListResponse,
    ItemPriceResponse,
    ItemPriceUpdate,
)
from app.services.item_price_service import ItemPriceService

router = APIRouter()


@router.post(
    "",
    response_model=ItemPriceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create item price",
    description="Create a new item price",
)
async def create_item_price(
    item_price_data: ItemPriceCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new item price.

    Requires authentication.

    **Request Body:**
    - **item_id**: Item UUID (required)
    - **price_list_id**: Price list UUID
    - **price**: Item price
    - **currency**: Currency code
    - **valid_from**: Valid from date
    - **valid_upto**: Valid until date
    - **min_qty**: Minimum quantity for this price
    - **extra_data**: Additional data

    **Returns:** Created item price details
    """
    item_price_service = ItemPriceService(db)
    item_price = item_price_service.create_item_price(
        item_price_data=item_price_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ItemPriceResponse.model_validate(item_price)


@router.post(
    "/bulk",
    response_model=ItemPriceBulkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create item prices",
    description="Create multiple item prices in a single request",
)
async def bulk_create_item_prices(
    bulk_data: ItemPriceBulkCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Bulk create item prices.

    Requires authentication.

    **Request Body:**
    - **item_prices**: List of item prices to create (max 100)

    **Returns:** Bulk creation results with created prices and any errors
    """
    item_price_service = ItemPriceService(db)
    created_prices, errors = item_price_service.bulk_create_item_prices(
        bulk_data=bulk_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )

    return ItemPriceBulkResponse(
        created_count=len(created_prices),
        item_prices=[ItemPriceResponse.model_validate(ip) for ip in created_prices],
        errors=errors,
    )


@router.get(
    "",
    response_model=ItemPriceListResponse,
    summary="List item prices",
    description="Get paginated list of item prices with optional filters",
)
async def list_item_prices(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    item_id: UUID | None = Query(None, description="Filter by item ID"),
    price_list_id: UUID | None = Query(None, description="Filter by price list ID"),
    currency: str | None = Query(None, description="Filter by currency"),
    valid_on: datetime | None = Query(None, description="Filter by validity date"),
    search: str | None = Query(None, description="Search in item code, name"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    include_item: bool = Query(False, description="Include item details"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List item prices with pagination and filters.

    Requires authentication.

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **item_id**: Filter by item ID
    - **price_list_id**: Filter by price list ID
    - **currency**: Filter by currency
    - **valid_on**: Filter by validity date (ISO format)
    - **search**: Search term for item code, name
    - **sort_by**: Field to sort by (default: created_at)
    - **sort_order**: Sort order - asc or desc (default: desc)
    - **include_item**: Include item details (default: false)

    **Returns:** Paginated list of item prices
    """
    item_price_service = ItemPriceService(db)

    item_prices, pagination = item_price_service.get_item_prices(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        item_id=item_id,
        price_list_id=price_list_id,
        currency=currency,
        valid_on=valid_on,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        include_item=include_item,
    )

    # Convert to response schema
    item_price_items = [ItemPriceListItem.model_validate(ip) for ip in item_prices]

    return ItemPriceListResponse(
        item_prices=item_price_items, pagination=PaginationMeta(**pagination)
    )


@router.get(
    "/{item_price_id}",
    response_model=ItemPriceResponse,
    summary="Get item price",
    description="Get item price details by ID",
)
async def get_item_price(
    item_price_id: UUID,
    include_item: bool = Query(False, description="Include item details"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get item price details by ID.

    Requires authentication.

    **Path Parameters:**
    - **item_price_id**: Item Price UUID

    **Query Parameters:**
    - **include_item**: Include item details (default: false)

    **Returns:** Item price details
    """
    item_price_service = ItemPriceService(db)
    item_price = item_price_service.get_item_price_by_id(
        item_price_id=item_price_id,
        organization_id=current_user.organization_id,
        include_item=include_item,
    )
    return ItemPriceResponse.model_validate(item_price)


@router.put(
    "/{item_price_id}",
    response_model=ItemPriceResponse,
    summary="Update item price",
    description="Update an existing item price",
)
async def update_item_price(
    item_price_id: UUID,
    item_price_data: ItemPriceUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing item price.

    Requires authentication.

    **Path Parameters:**
    - **item_price_id**: Item Price UUID

    **Request Body:** Fields to update (all optional)

    **Returns:** Updated item price details
    """
    item_price_service = ItemPriceService(db)
    item_price = item_price_service.update_item_price(
        item_price_id=item_price_id,
        item_price_data=item_price_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ItemPriceResponse.model_validate(item_price)


@router.delete(
    "/{item_price_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item price",
    description="Delete an item price",
)
async def delete_item_price(
    item_price_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete an item price.

    Requires authentication.

    **Path Parameters:**
    - **item_price_id**: Item Price UUID

    **Returns:** 204 No Content on success
    """
    item_price_service = ItemPriceService(db)
    item_price_service.delete_item_price(
        item_price_id=item_price_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return None


@router.get(
    "/by-item/{item_id}",
    response_model=list[ItemPriceResponse],
    summary="Get item prices by item",
    description="Get all item prices for a specific item",
)
async def get_item_prices_by_item(
    item_id: UUID,
    valid_on: datetime | None = Query(None, description="Filter by validity date"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get all item prices for a specific item.

    Requires authentication.

    **Path Parameters:**
    - **item_id**: Item UUID

    **Query Parameters:**
    - **valid_on**: Filter by validity date (ISO format)

    **Returns:** List of item prices for the item
    """
    item_price_service = ItemPriceService(db)
    item_prices = item_price_service.get_item_prices_by_item(
        item_id=item_id,
        organization_id=current_user.organization_id,
        valid_on=valid_on,
    )
    return [ItemPriceResponse.model_validate(ip) for ip in item_prices]
