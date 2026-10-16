"""Internal Warehouse-User Assignment API

Service-to-service endpoint called by the Identity Service when creating
warehouse worker users. No user authentication required — protected by
network-level security (internal Docker network).
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_internal_service
from app.services.warehouse_user_service import WarehouseUserService

logger = logging.getLogger(__name__)

router = APIRouter()


class InternalWarehouseUserCreateRequest(BaseModel):
    """Request body for internal warehouse-user assignment."""

    user_id: UUID = Field(..., description="UUID of the worker user")
    organization_id: UUID = Field(..., description="UUID of the organization")
    warehouse_id: UUID = Field(..., description="UUID of the warehouse to assign")
    role: str = Field(
        default="operator",
        description="Warehouse role (supervisor, manager, operator, coordinator)",
    )
    is_primary: bool = Field(
        default=False, description="If True, user sees all warehouses"
    )


class InternalWarehouseUserResponse(BaseModel):
    """Response body for internal warehouse-user assignment."""

    success: bool
    user_id: UUID
    warehouse_id: UUID
    role: str
    message: str


@router.post(
    "/internal/warehouse-users",
    response_model=InternalWarehouseUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a user to a warehouse (internal service-to-service)",
    description=(
        "Creates a WarehouseUser record linking a user to a warehouse. "
        "Called by the Identity Service during warehouse worker creation. "
        "Protected by the X-Internal-Secret shared-secret header."
    ),
    tags=["Internal"],
)
async def internal_assign_user_to_warehouse(
    request: InternalWarehouseUserCreateRequest,
    db: Session = Depends(get_db),
    _auth: None = Depends(require_internal_service),
) -> InternalWarehouseUserResponse:
    """
    Internal endpoint to assign a user to a warehouse.

    Called by Identity Service when creating warehouse worker users.
    Idempotent — if the assignment already exists, the existing record is updated.
    """
    svc = WarehouseUserService(db)
    try:
        data = svc.create(
            data={
                "user_id": request.user_id,
                "warehouse_id": request.warehouse_id,
                "role": request.role,
                "is_primary": request.is_primary,
                "is_active": True,
            },
            organization_id=request.organization_id,
            created_by=request.user_id,  # system-created; user_id as created_by
        )
        db.commit()
        logger.info(
            "Internal warehouse assignment created",
            extra={
                "user_id": str(request.user_id),
                "warehouse_id": str(request.warehouse_id),
                "role": request.role,
                "event": "internal_warehouse_user_created",
            },
        )
        return InternalWarehouseUserResponse(
            success=True,
            user_id=request.user_id,
            warehouse_id=request.warehouse_id,
            role=data.role.value if data.role else request.role,
            message="User assigned to warehouse successfully",
        )
    except Exception as exc:
        logger.error(
            "Failed to create internal warehouse assignment",
            extra={
                "user_id": str(request.user_id),
                "warehouse_id": str(request.warehouse_id),
                "error": str(exc),
                "event": "internal_warehouse_user_failed",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign user to warehouse: {str(exc)}",
        )


class InternalWarehouseUserItem(BaseModel):
    """A single warehouse→user assignment."""

    id: UUID
    user_id: UUID
    warehouse_id: UUID
    role: str
    is_primary: bool
    is_active: bool


class InternalWarehouseUserListResponse(BaseModel):
    """Response body for internal assignment reads."""

    users: list[InternalWarehouseUserItem]


def _parse_user_ids(raw: str | None) -> list[UUID] | None:
    """Parse a comma-separated list of UUIDs, raising 400 on malformed input."""
    if not raw:
        return None
    try:
        return [UUID(part.strip()) for part in raw.split(",") if part.strip()]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user_ids: {exc}",
        ) from exc


@router.get(
    "/internal/warehouse-users",
    response_model=InternalWarehouseUserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List warehouse-user assignments (internal service-to-service)",
    description=(
        "Returns warehouse↔user assignments for an organization so the Identity "
        "Service can resolve a worker's assigned warehouses without reading the "
        "core ``warehouse_users`` table directly. "
        "Filter by ``user_ids`` (comma-separated) and/or ``warehouse_id``. "
        "Protected by the X-Internal-Secret shared-secret header."
    ),
    tags=["Internal"],
)
async def internal_list_warehouse_users(
    organization_id: UUID | None = Query(
        None, description="Optional organization to scope the query"
    ),
    user_ids: str | None = Query(
        None, description="Comma-separated user UUIDs to filter by"
    ),
    warehouse_id: UUID | None = Query(
        None, description="Only assignments for this warehouse"
    ),
    is_active: bool = Query(True, description="Filter on the is_active flag"),
    db: Session = Depends(get_db),
    _auth: None = Depends(require_internal_service),
) -> InternalWarehouseUserListResponse:
    """List assignments, primary rows first, unpaginated."""
    svc = WarehouseUserService(db)
    rows = svc.list_assignments(
        organization_id=organization_id,
        user_ids=_parse_user_ids(user_ids),
        warehouse_id=warehouse_id,
        is_active=is_active,
    )

    return InternalWarehouseUserListResponse(
        users=[
            InternalWarehouseUserItem(
                id=row.id,
                user_id=row.user_id,
                warehouse_id=row.warehouse_id,
                role=row.role.value if row.role else "operator",
                is_primary=bool(row.is_primary),
                is_active=bool(row.is_active),
            )
            for row in rows
        ]
    )
