"""Warehouse-user assignment API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
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


class PendingAssignmentPayload(BaseModel):
    email: str
    warehouse_ids: list[UUID]
    role: str = "operator"
    is_primary: bool = False


@router.post(
    "", response_model=WarehouseUserResponse, status_code=status.HTTP_201_CREATED
)
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


@router.post("/pending", status_code=status.HTTP_201_CREATED)
async def create_pending_assignments(
    body: PendingAssignmentPayload,
    current_user: CurrentUser = Depends(require_permission("warehouse.manage")),
    db: Session = Depends(get_db),
):
    """Store warehouse assignments keyed by email for a not-yet-accepted invitation.

    When the invited user logs in and calls /my-warehouses,
    these pending rows are resolved into actual warehouse_users rows.
    """
    svc = WarehouseUserService(db)
    for wh_id in body.warehouse_ids:
        svc.create_pending(
            email=body.email,
            organization_id=current_user.organization_id,
            warehouse_id=wh_id,
            role=body.role,
            is_primary=body.is_primary,
            created_by=current_user.id,
        )
    db.commit()
    return {"created": len(body.warehouse_ids)}


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

    - System admins see all warehouses.
    - Users with a primary assignment see all warehouses.
    - Everyone else sees only their assigned warehouses.
    - Pending assignments (by email) are resolved on first call.
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        "[my-warehouses] user_id=%s org_id=%s user_type=%s email=%s",
        current_user.id,
        current_user.organization_id,
        current_user.user_type,
        current_user.email,
    )
    # Global access: only system_admin, org_admin, or super admin (*.*).
    # WMS roles (manager, operator) are scoped by WarehouseUser assignments.
    has_global_access = (
        current_user.user_type in ("system_admin", "organization_admin")
        or "*.*" in current_user.permissions
    )

    if has_global_access:
        from app.models.warehouse import Warehouse

        warehouses = (
            db.query(Warehouse)
            .filter(
                Warehouse.organization_id == current_user.organization_id,
                Warehouse.is_active == True,
            )
            .order_by(Warehouse.name)
            .all()
        )
        logger.info(
            "[my-warehouses] global access path: returned %d warehouses",
            len(warehouses),
        )
        return {
            "warehouses": [
                {
                    "id": w.id,
                    "name": w.name,
                    "code": w.code,
                    "city": w.city,
                    "type": w.warehouse_type.value if w.warehouse_type else None,
                    "is_default": w.is_default,
                }
                for w in warehouses
            ]
        }

    svc = WarehouseUserService(db)
    warehouses = svc.get_user_warehouses(current_user)
    logger.info("[my-warehouses] returned %d warehouses", len(warehouses))
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
