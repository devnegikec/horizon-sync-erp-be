"""Item Group management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.common import PaginationMeta
from app.schemas.item_group import (
    ItemGroupCreate,
    ItemGroupListItem,
    ItemGroupListResponse,
    ItemGroupResponse,
    ItemGroupTreeNode,
    ItemGroupUpdate,
)
from app.services.item_group_service import ItemGroupService

router = APIRouter()


@router.post(
    "",
    response_model=ItemGroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create item group",
    description="Create a new item group",
)
async def create_item_group(
    item_group_data: ItemGroupCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new item group.

    Requires authentication.

    **Request Body:**
    - **name**: Item group name (required)
    - **code**: Unique item group code (required)
    - **description**: Item group description
    - **parent_id**: Parent item group for hierarchy
    - **default_valuation_method**: Default valuation (fifo, lifo, moving_average, standard)
    - **default_uom**: Default unit of measure
    - **is_active**: Active status (default: true)

    **Returns:** Created item group details
    """
    item_group_service = ItemGroupService(db)
    item_group = item_group_service.create_item_group(
        item_group_data=item_group_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ItemGroupResponse.model_validate(item_group)


@router.get(
    "",
    response_model=ItemGroupListResponse,
    summary="List item groups",
    description="Get paginated list of item groups with optional filters",
)
async def list_item_groups(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    parent_id: UUID | None = Query(None, description="Filter by parent item group ID"),
    search: str | None = Query(None, description="Search in name, code"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List item groups with pagination and filters.

    Requires authentication.

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **is_active**: Filter by active status
    - **parent_id**: Filter by parent item group
    - **search**: Search term for name, code
    - **sort_by**: Field to sort by (default: created_at)
    - **sort_order**: Sort order - asc or desc (default: desc)

    **Returns:** Paginated list of item groups
    """
    item_group_service = ItemGroupService(db)

    item_groups, pagination = item_group_service.get_item_groups(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        is_active=is_active,
        parent_id=parent_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Convert to response schema
    item_group_items = [ItemGroupListItem.model_validate(ig) for ig in item_groups]

    return ItemGroupListResponse(
        item_groups=item_group_items, pagination=PaginationMeta(**pagination)
    )


@router.get(
    "/tree",
    response_model=list[ItemGroupTreeNode],
    summary="Get item group tree",
    description="Get item groups as a hierarchical tree structure",
)
async def get_item_group_tree(
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get item groups as a tree structure.

    Requires authentication.

    **Returns:** List of root-level item groups with nested children
    """
    item_group_service = ItemGroupService(db)
    return item_group_service.get_item_group_tree(current_user.organization_id)


@router.get(
    "/active",
    response_model=list[ItemGroupListItem],
    summary="Get active item groups",
    description="Get all active item groups in the organization as a flat list",
)
async def get_active_item_groups(
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get all active item groups.

    Requires authentication.

    **Returns:** List of active item groups
    """
    item_group_service = ItemGroupService(db)
    item_groups = item_group_service.get_active_item_groups(
        current_user.organization_id
    )
    return [ItemGroupListItem.model_validate(ig) for ig in item_groups]


@router.get(
    "/{item_group_id}",
    response_model=ItemGroupResponse,
    summary="Get item group",
    description="Get item group details by ID",
)
async def get_item_group(
    item_group_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get item group details by ID.

    Requires authentication.

    **Path Parameters:**
    - **item_group_id**: Item Group UUID

    **Returns:** Item group details including parent info
    """
    item_group_service = ItemGroupService(db)
    item_group = item_group_service.get_item_group_by_id(
        item_group_id=item_group_id,
        organization_id=current_user.organization_id,
        include_parent=True,
    )
    return ItemGroupResponse.model_validate(item_group)


@router.put(
    "/{item_group_id}",
    response_model=ItemGroupResponse,
    summary="Update item group",
    description="Update an existing item group",
)
async def update_item_group(
    item_group_id: UUID,
    item_group_data: ItemGroupUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing item group.

    Requires authentication.

    **Path Parameters:**
    - **item_group_id**: Item Group UUID

    **Request Body:** Fields to update (all optional)

    **Returns:** Updated item group details
    """
    item_group_service = ItemGroupService(db)
    item_group = item_group_service.update_item_group(
        item_group_id=item_group_id,
        item_group_data=item_group_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ItemGroupResponse.model_validate(item_group)


@router.delete(
    "/{item_group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item group",
    description="Soft delete an item group",
)
async def delete_item_group(
    item_group_id: UUID,
    force: bool = Query(
        False, description="Force delete even if has children or items"
    ),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Soft delete an item group.

    Requires authentication.

    **Path Parameters:**
    - **item_group_id**: Item Group UUID

    **Query Parameters:**
    - **force**: Force delete even if has children or items (default: false)

    **Returns:** 204 No Content on success
    """
    item_group_service = ItemGroupService(db)
    item_group_service.delete_item_group(
        item_group_id=item_group_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        force=force,
    )
    return None
