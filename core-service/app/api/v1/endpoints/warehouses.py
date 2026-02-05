"""Warehouse management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    WAREHOUSE_CREATE,
    WAREHOUSE_DELETE,
    WAREHOUSE_READ,
    WAREHOUSE_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseListItem,
    WarehouseListResponse,
    WarehouseResponse,
    WarehouseStatusCounts,
    WarehouseTreeNode,
    WarehouseTypeCounts,
    WarehouseUpdate,
)
from app.services.warehouse_service import WarehouseService

router = APIRouter()


@router.post(
    "",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create warehouse",
    description="Create a new warehouse",
)
async def create_warehouse(
    warehouse_data: WarehouseCreate,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Create a new warehouse.

    Requires authentication.

    **Request Body:**
    - **name**: Warehouse name (required)
    - **code**: Unique warehouse code (required)
    - **description**: Warehouse description
    - **warehouse_type**: Type (warehouse, store, virtual, transit)
    - **parent_warehouse_id**: Parent warehouse for hierarchy
    - **address_line1, city, state, etc.**: Address information
    - **contact_name, contact_phone, contact_email**: Contact information
    - **total_capacity, capacity_uom**: Capacity information
    - **is_active**: Active status (default: true)
    - **is_default**: Default warehouse flag

    **Returns:** Created warehouse details
    """
    warehouse_service = WarehouseService(db)
    warehouse = warehouse_service.create_warehouse(
        warehouse_data=warehouse_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return WarehouseResponse.model_validate(warehouse)


@router.get(
    "",
    response_model=WarehouseListResponse,
    summary="List warehouses",
    description="Get paginated list of warehouses with optional filters",
)
async def list_warehouses(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    warehouse_type: str | None = Query(
        None, description="Filter by type (warehouse, store, virtual, transit)"
    ),
    parent_warehouse_id: UUID | None = Query(
        None, description="Filter by parent warehouse ID"
    ),
    search: str | None = Query(None, description="Search in name, code, city"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    List warehouses with pagination and filters.

    Requires authentication.

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **is_active**: Filter by active status
    - **warehouse_type**: Filter by warehouse type
    - **parent_warehouse_id**: Filter by parent warehouse
    - **search**: Search term for name, code, city
    - **sort_by**: Field to sort by (default: created_at)
    - **sort_order**: Sort order - asc or desc (default: desc)

    **Returns:** Paginated list of warehouses with status and type counts
    """
    warehouse_service = WarehouseService(db)

    (
        warehouses,
        pagination,
        status_counts,
        type_counts,
    ) = warehouse_service.get_warehouses(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        is_active=is_active,
        warehouse_type=warehouse_type,
        parent_warehouse_id=parent_warehouse_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Convert to response schema
    warehouse_items = [WarehouseListItem.model_validate(w) for w in warehouses]

    return WarehouseListResponse(
        warehouses=warehouse_items,
        pagination=PaginationMeta(**pagination),
        status_counts=WarehouseStatusCounts(**status_counts),
        type_counts=WarehouseTypeCounts(**type_counts),
    )


@router.get(
    "/tree",
    response_model=list[WarehouseTreeNode],
    summary="Get warehouse tree",
    description="Get warehouses as a hierarchical tree structure",
)
async def get_warehouse_tree(
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get warehouses as a tree structure.

    Requires authentication.

    **Returns:** List of root-level warehouses with nested children
    """
    warehouse_service = WarehouseService(db)
    return warehouse_service.get_warehouse_tree(current_user.organization_id)


@router.get(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    summary="Get warehouse",
    description="Get warehouse details by ID",
)
async def get_warehouse(
    warehouse_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get warehouse details by ID.

    Requires authentication.

    **Path Parameters:**
    - **warehouse_id**: Warehouse UUID

    **Returns:** Warehouse details including parent info
    """
    warehouse_service = WarehouseService(db)
    warehouse = warehouse_service.get_warehouse_by_id(
        warehouse_id=warehouse_id,
        organization_id=current_user.organization_id,
        include_parent=True,
    )
    return WarehouseResponse.model_validate(warehouse)


@router.put(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    summary="Update warehouse",
    description="Update an existing warehouse",
)
async def update_warehouse(
    warehouse_id: UUID,
    warehouse_data: WarehouseUpdate,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Update an existing warehouse.

    Requires authentication.

    **Path Parameters:**
    - **warehouse_id**: Warehouse UUID

    **Request Body:** Fields to update (all optional)

    **Returns:** Updated warehouse details
    """
    warehouse_service = WarehouseService(db)
    warehouse = warehouse_service.update_warehouse(
        warehouse_id=warehouse_id,
        warehouse_data=warehouse_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return WarehouseResponse.model_validate(warehouse)


@router.delete(
    "/{warehouse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete warehouse",
    description="Soft delete a warehouse",
)
async def delete_warehouse(
    warehouse_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_DELETE)),
    db: Session = Depends(get_db),
):
    """
    Soft delete a warehouse.

    Requires authentication.

    **Path Parameters:**
    - **warehouse_id**: Warehouse UUID

    **Returns:** 204 No Content on success
    """
    warehouse_service = WarehouseService(db)
    warehouse_service.delete_warehouse(
        warehouse_id=warehouse_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return None
