"""Location allocation API endpoints for managing location-to-item-group allocations"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import WAREHOUSE_CREATE, WAREHOUSE_READ, WAREHOUSE_UPDATE
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.location_allocation import (
    CreateAllocationRequest,
    LocationAllocationResponse,
    PaginatedAllocations,
    UpdateAllocationRequest,
)
from app.services.location_allocation_service import LocationAllocationService

router = APIRouter()


@router.post(
    "",
    response_model=LocationAllocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create location allocation",
    description="Create a location allocation linking a location to an item group",
)
async def create_allocation(
    data: CreateAllocationRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Create a location allocation.

    Links a location (bin, level, or bay) to an item group for put-away prioritization.

    **Request Body:**
    - **location_id**: Location UUID (bin, level, or bay)
    - **item_group_id**: Item group UUID to allocate
    - **allocation_type**: 'exclusive' or 'preferred' (default: 'preferred')
    - **priority**: Priority for put-away ordering (default: 0)

    **Returns:** Created allocation record
    """
    service = LocationAllocationService(db)
    allocation = service.create_allocation(
        location_id=data.location_id,
        item_group_id=data.item_group_id,
        organization_id=current_user.organization_id,
        allocation_type=data.allocation_type,
        priority=data.priority,
    )
    return LocationAllocationResponse.model_validate(allocation)


@router.get(
    "",
    response_model=PaginatedAllocations,
    summary="List location allocations",
    description="Get paginated list of location allocations with optional filters",
)
async def list_allocations(
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse UUID"),
    item_group_id: UUID | None = Query(None, description="Filter by item group UUID"),
    location_type: str | None = Query(
        None, description="Filter by location type (zone, aisle, bay, level, bin)"
    ),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    List location allocations with optional filters and pagination.

    **Query Parameters:**
    - **warehouse_id**: Filter by warehouse (via location's warehouse_id)
    - **item_group_id**: Filter by item group
    - **location_type**: Filter by location type
    - **is_active**: Filter by active status
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 50, max: 100)

    **Returns:** Paginated list of allocations
    """
    service = LocationAllocationService(db)
    result = service.list_allocations(
        organization_id=current_user.organization_id,
        warehouse_id=warehouse_id,
        item_group_id=item_group_id,
        location_type=location_type,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )

    allocations = [
        LocationAllocationResponse.model_validate(a) for a in result["allocations"]
    ]

    return PaginatedAllocations(
        allocations=allocations,
        pagination=PaginationMeta(**result["pagination"]),
    )


@router.get(
    "/{allocation_id}",
    response_model=LocationAllocationResponse,
    summary="Get location allocation",
    description="Get a single location allocation by ID",
)
async def get_allocation(
    allocation_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get a single location allocation by ID.

    **Path Parameters:**
    - **allocation_id**: Allocation UUID

    **Returns:** Allocation details
    """
    service = LocationAllocationService(db)
    allocation = service._get_allocation(
        allocation_id=allocation_id,
        organization_id=current_user.organization_id,
    )
    return LocationAllocationResponse.model_validate(allocation)


@router.patch(
    "/{allocation_id}",
    response_model=LocationAllocationResponse,
    summary="Update location allocation",
    description="Update allocation type or priority",
)
async def update_allocation(
    allocation_id: UUID,
    data: UpdateAllocationRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Update a location allocation's mutable fields.

    **Path Parameters:**
    - **allocation_id**: Allocation UUID

    **Request Body:** Fields to update (all optional)
    - **allocation_type**: New allocation type ('exclusive' or 'preferred')
    - **priority**: New priority value

    **Returns:** Updated allocation details
    """
    service = LocationAllocationService(db)
    allocation = service.update_allocation(
        allocation_id=allocation_id,
        organization_id=current_user.organization_id,
        allocation_type=data.allocation_type,
        priority=data.priority,
    )
    return LocationAllocationResponse.model_validate(allocation)


@router.post(
    "/{allocation_id}/deactivate",
    response_model=LocationAllocationResponse,
    summary="Deactivate location allocation",
    description="Set a location allocation as inactive",
)
async def deactivate_allocation(
    allocation_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Deactivate a location allocation.

    Sets is_active=False on the allocation record.

    **Path Parameters:**
    - **allocation_id**: Allocation UUID

    **Returns:** The deactivated allocation
    """
    service = LocationAllocationService(db)
    allocation = service.deactivate_allocation(
        allocation_id=allocation_id,
        organization_id=current_user.organization_id,
    )
    return LocationAllocationResponse.model_validate(allocation)
