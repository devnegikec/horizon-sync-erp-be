"""Warehouse-user assignment API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.warehouse_user import (
    WarehouseUserCreate,
    WarehouseUserListResponse,
    WarehouseUserResponse,
    WarehouseUserUpdate,
)
from app.services.warehouse_user_service import WarehouseUserService

router = APIRouter()


@router.post("", response_model=WarehouseUserResponse, status_code=status.HTTP_201_CREATED)
async def assign_user_to_warehouse(
    body: WarehouseUserCreate,
    current_user: CurrentUser = Depends(require_permission("warehouse.manage")),
    db: Session = Depends(get_db),
):
    """Assign a user to a warehouse with a specific role."""
    svc = WarehouseUserService(db)
    data = svc.create(
        data=body.model_dump(),
        organization_id=current_user.organization_id,
        created_by=current_user.id,
    )
    return WarehouseUserResponse.model_validate(data)


@router.get("", response_model=WarehouseUserListResponse)
async def list_warehouse_users(
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse"),
    user_id: UUID | None = Query(None, description="Filter by user"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permission("warehouse.read")),
    db: Session = Depends(get_db),
):
    """List warehouse-user assignments."""
    svc = WarehouseUserService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        warehouse_id=warehouse_id,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )
    return WarehouseUserListResponse(
        users=[WarehouseUserResponse.model_validate(x) for x in items],
        pagination=pagination,
    )


@router.get("/my-warehouses")
async def get_my_warehouses(
    current_user: CurrentUser = Depends(require_permission("warehouse.read")),
    db: Session = Depends(get_db),
):
    """Get warehouses assigned to the current user.

    If user has no explicit assignments, returns all active warehouses
    for the organization (fallback for backward compatibility).
    """
    svc = WarehouseUserService(db)
    warehouses = svc.get_user_warehouses(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    return {"warehouses": warehouses}


@router.patch("/{assignment_id}", response_model=WarehouseUserResponse)
async def update_warehouse_user(
    assignment_id: UUID,
    body: WarehouseUserUpdate,
    current_user: CurrentUser = Depends(require_permission("warehouse.manage")),
    db: Session = Depends(get_db),
):
    """Update a warehouse-user assignment."""
    svc = WarehouseUserService(db)
    data = svc.update(
        assignment_id=assignment_id,
        data=body.model_dump(exclude_none=True),
        organization_id=current_user.organization_id,
    )
    return WarehouseUserResponse.model_validate(data)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_warehouse_user(
    assignment_id: UUID,
    current_user: CurrentUser = Depends(require_permission("warehouse.manage")),
    db: Session = Depends(get_db),
):
    """Remove a user from a warehouse."""
    svc = WarehouseUserService(db)
    svc.delete(
        assignment_id=assignment_id,
        organization_id=current_user.organization_id,
    )
    return None
