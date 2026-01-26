"""Item management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.common import PaginationMeta
from app.schemas.item import (
    ItemCreate,
    ItemListItem,
    ItemListResponse,
    ItemResponse,
    ItemUpdate,
)
from app.services.item_service import ItemService

router = APIRouter()


@router.post(
    "",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create item",
    description="Create a new inventory item",
)
async def create_item(
    item_data: ItemCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new inventory item.

    Requires authentication.

    **Request Body:**
    - **item_code**: Unique item code (required)
    - **item_name**: Item name (required)
    - **description**: Item description
    - **uom**: Unit of measure (default: Nos) (e.g. Kg, Nos, L, etc.)
    - **maintain_stock**: Track inventory levels (default: true)
    - **standard_rate**: Standard selling rate
    - **valuation_rate**: Valuation rate for inventory
    - And more...

    **Returns:** Created item details
    """
    item_service = ItemService(db)
    item = item_service.create_item(
        item_data=item_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ItemResponse.model_validate(item)


@router.get(
    "",
    response_model=ItemListResponse,
    summary="List items",
    description="Get paginated list of items with optional filters",
)
async def list_items(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    status: str | None = Query(
        None, description="Filter by status (active, inactive, discontinued)"
    ),
    item_type: str | None = Query(
        None,
        description="Filter by item type (stock, non_stock, service, fixed_asset)",
    ),
    item_group_id: UUID | None = Query(None, description="Filter by item group ID"),
    maintain_stock: bool | None = Query(
        None, description="Filter by maintain_stock flag"
    ),
    search: str | None = Query(
        None, description="Search in item_code, item_name, barcode"
    ),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List inventory items with pagination and filters.

    Requires authentication.

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **status**: Filter by item status
    - **item_type**: Filter by item type
    - **item_group_id**: Filter by item group
    - **maintain_stock**: Filter by inventory tracking flag
    - **search**: Search term for item_code, item_name, barcode
    - **sort_by**: Field to sort by (default: created_at)
    - **sort_order**: Sort order - asc or desc (default: desc)

    **Returns:** Paginated list of items
    """
    item_service = ItemService(db)

    items, pagination = item_service.get_items(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        status=status,
        item_type=item_type,
        item_group_id=item_group_id,
        maintain_stock=maintain_stock,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Convert to response schema
    item_items = [ItemListItem.model_validate(item) for item in items]

    return ItemListResponse(items=item_items, pagination=PaginationMeta(**pagination))


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get item",
    description="Get item details by ID",
)
async def get_item(
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get inventory item details by ID.

    Requires authentication.

    **Path Parameters:**
    - **item_id**: Item UUID

    **Returns:** Item details including item group info
    """
    item_service = ItemService(db)
    item = item_service.get_item_by_id(
        item_id=item_id,
        organization_id=current_user.organization_id,
        include_group=True,
    )
    return ItemResponse.model_validate(item)


@router.put(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Update item",
    description="Update an existing item",
)
async def update_item(
    item_id: UUID,
    item_data: ItemUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing inventory item.

    Requires authentication.

    **Path Parameters:**
    - **item_id**: Item UUID

    **Request Body:** Fields to update (all optional)

    **Returns:** Updated item details
    """
    item_service = ItemService(db)
    item = item_service.update_item(
        item_id=item_id,
        item_data=item_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ItemResponse.model_validate(item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item",
    description="Soft delete an item",
)
async def delete_item(
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Soft delete an inventory item.

    Requires authentication.

    **Path Parameters:**
    - **item_id**: Item UUID

    **Returns:** 204 No Content on success
    """
    item_service = ItemService(db)
    item_service.delete_item(
        item_id=item_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return None
