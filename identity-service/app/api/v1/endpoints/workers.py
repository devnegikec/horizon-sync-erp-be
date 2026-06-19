"""Warehouse Workers Management endpoints for identity-service

CRUD for warehouse worker users (user_type=warehouse_worker).
Accessible to system_admin and organization_admin users.
Mounted under /identity prefix (NOT /identity/admin).
"""

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import get_db
from app.dependencies import CurrentUser, get_core_service_client, get_current_active_user
from app.models.base import UserStatus, UserType
from app.models.role import Role, UserOrganizationRole
from app.models.user import User
from app.schemas.admin import (
    CreateWarehouseWorkerRequest,
    WarehouseWorkerListResponse,
    WarehouseWorkerResponse,
    WarehouseWorkerUpdateRequest,
)
from app.services.core_service_client import CoreServiceClient

logger = logging.getLogger(__name__)

router = APIRouter()


# ------------------------------------------------------------------
# Auth dependency: system_admin or organization_admin
# ------------------------------------------------------------------


async def require_worker_manager(
    current_user: CurrentUser = Depends(get_current_active_user),
) -> CurrentUser:
    """Allow system_admin, organization_admin, or users with warehouse.manage permission."""
    if current_user.user_type in (UserType.SYSTEM_ADMIN, UserType.ORGANIZATION_ADMIN):
        return current_user
    if "warehouse.manage" in current_user.permissions:
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin, org admin, or warehouse.manage permission required",
    )


# ------------------------------------------------------------------
# Helper: convert User model to response dict
# ------------------------------------------------------------------


def _user_to_response(user: User, warehouse_assignments: list[str] | None = None) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "display_name": user.display_name,
        "phone": user.phone,
        "user_type": user.user_type.value if user.user_type else "warehouse_worker",
        "status": user.status.value if user.status else "active",
        "is_active": user.is_active,
        "qr_code": user.qr_code,
        "organization_id": _get_org_id(user),
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "warehouse_assignments": warehouse_assignments or [],
    }


def _get_org_id(user: User) -> str | None:
    """Get the primary organization ID for a SQLAlchemy User model."""
    if user.user_organization_roles:
        for uor in user.user_organization_roles:
            if uor.is_active:
                return str(uor.organization_id)
    return None


def _get_org_id_from_current_user(current_user: CurrentUser, db: Session) -> str | None:
    """Get the primary organization ID for the current authenticated user.

    Looks up UserOrganizationRole from DB since CurrentUser (from JWT)
    does not carry organization info.
    """
    uor = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == current_user.id,
            UserOrganizationRole.is_active == True,
        )
        .order_by(UserOrganizationRole.is_primary.desc())
        .first()
    )
    return str(uor.organization_id) if uor else None


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.post(
    "/workers",
    response_model=WarehouseWorkerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a warehouse worker",
    description="Create a warehouse worker with QR code login and warehouse assignments.",
)
async def create_worker(
    body: CreateWarehouseWorkerRequest,
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
    core_client: CoreServiceClient | None = Depends(get_core_service_client),
):
    """Create a new warehouse worker user for QR code login.

    Accepts both formats:
    - New: { first_name, last_name, qr_code, organization_id, warehouse_ids }
    - Legacy WMS: { first_name, last_name, email, phone, login_username,
                     employee_id, password, role, warehouse_id }
    """
    # --- Resolve organization_id ---
    org_id = body.organization_id

    # --- Resolve QR code ---
    qr_code = body.qr_code
    if not qr_code:
        if body.employee_id:
            qr_code = body.employee_id  # use employee_id as QR code
        else:
            qr_code = f"WRK-{secrets.token_hex(6).upper()}"

    # --- Resolve email ---
    worker_email = body.email if body.email else f"{qr_code}@warehouse.local"

    # --- Resolve warehouse_ids (support both warehouse_id and warehouse_ids) ---
    warehouse_ids: list = []
    if body.warehouse_ids:
        warehouse_ids = list(body.warehouse_ids)
    if body.warehouse_id and body.warehouse_id not in warehouse_ids:
        warehouse_ids.append(body.warehouse_id)

    warehouse_role_str = body.warehouse_role or body.role or "operator"

    # --- Validate ---
    existing = (
        db.query(User)
        .filter(User.email == worker_email, User.deleted_at.is_(None))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email {worker_email} is already registered",
        )

    existing_qr = db.query(User).filter(User.qr_code == qr_code).first()
    if existing_qr:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"QR code {qr_code} is already in use",
        )

    # Find the warehouse_work_user role
    ww_role = (
        db.query(Role)
        .filter(Role.code == "warehouse_work_user", Role.is_active == True)  # noqa: E712
        .first()
    )
    if not ww_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="warehouse_work_user role not found. Run seed data first.",
        )

    # --- Build extra_data for legacy fields ---
    extra_data = {}
    if body.login_username:
        extra_data["login_username"] = body.login_username
    if body.employee_id:
        extra_data["employee_id"] = body.employee_id

    # --- Password: hash if provided, else generate random ---
    if body.password:
        password_hash = hash_password(body.password)
    else:
        password_hash = hash_password(secrets.token_urlsafe(16))

    # --- Create user ---
    user = User(
        email=worker_email,
        password_hash=password_hash,
        first_name=body.first_name,
        last_name=body.last_name,
        display_name=f"{body.first_name} {body.last_name}",
        phone=body.phone,
        user_type=UserType.WAREHOUSE_WORKER,
        status=UserStatus.ACTIVE,
        is_active=True,
        email_verified=True,
        qr_code=qr_code,
        extra_data=extra_data if extra_data else None,
    )
    db.add(user)
    db.flush()

    # Assign the warehouse_work_user role
    db.add(UserOrganizationRole(
        user_id=user.id,
        organization_id=org_id,
        role_id=ww_role.id,
        is_primary=True,
        is_active=True,
        status="active",
    ))
    db.commit()
    db.refresh(user)

    # --- Assign warehouse access ---
    if warehouse_ids and core_client:
        for wh_id in warehouse_ids:
            try:
                await core_client.assign_user_to_warehouse(
                    user_id=user.id,
                    organization_id=org_id,
                    warehouse_id=wh_id,
                    role=warehouse_role_str,
                )
            except Exception as exc:
                logger.error(
                    "Failed to assign worker to warehouse",
                    extra={"user_id": str(user.id), "warehouse_id": str(wh_id), "error": str(exc)},
                )

    return WarehouseWorkerResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        phone=user.phone,
        user_type=user.user_type.value,
        status=user.status.value,
        is_active=user.is_active,
        qr_code=user.qr_code,
        organization_id=str(org_id),
        created_at=user.created_at,
        warehouse_assignments=[str(wid) for wid in warehouse_ids],
    )


@router.get(
    "/workers",
    response_model=WarehouseWorkerListResponse,
    summary="List warehouse workers",
    description="List all warehouse worker users. Requires admin or org admin.",
)
async def list_workers(
    search: str | None = Query(None, description="Search by name, email, or QR code"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status: active, inactive"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
):
    """List warehouse worker users with pagination and filters."""
    # Look up org from DB (CurrentUser from JWT doesn't carry org info)
    org_id = _get_org_id_from_current_user(current_user, db)

    query = db.query(User).filter(
        User.user_type == UserType.WAREHOUSE_WORKER,
        User.deleted_at.is_(None),
    )

    # Scope to organization if not system admin
    if current_user.user_type != UserType.SYSTEM_ADMIN and org_id:
        query = query.join(
            UserOrganizationRole,
            UserOrganizationRole.user_id == User.id,
        ).filter(
            UserOrganizationRole.organization_id == org_id,
            UserOrganizationRole.is_active == True,
        )

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.first_name.ilike(search_term))
            | (User.last_name.ilike(search_term))
            | (User.email.ilike(search_term))
            | (User.qr_code.ilike(search_term))
        )

    if status_filter:
        if status_filter == "active":
            query = query.filter(User.is_active == True)
        elif status_filter == "inactive":
            query = query.filter(User.is_active == False)

    total = query.count()
    total_pages = (total + page_size - 1) // page_size if page_size else 0

    users = (
        query.order_by(User.first_name, User.last_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return WarehouseWorkerListResponse(
        workers=[WarehouseWorkerResponse(**_user_to_response(u)) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/workers/{worker_id}",
    response_model=WarehouseWorkerResponse,
    summary="Get warehouse worker",
    description="Get a single warehouse worker by ID.",
)
async def get_worker(
    worker_id: str,
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
):
    """Get a warehouse worker user by ID."""
    from uuid import UUID as _UUID

    user = (
        db.query(User)
        .filter(
            User.id == _UUID(worker_id),
            User.user_type == UserType.WAREHOUSE_WORKER,
            User.deleted_at.is_(None),
        )
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    return WarehouseWorkerResponse(**_user_to_response(user))


@router.patch(
    "/workers/{worker_id}",
    response_model=WarehouseWorkerResponse,
    summary="Update warehouse worker",
    description="Update a warehouse worker's details. Requires admin or org admin.",
)
async def update_worker(
    worker_id: str,
    body: WarehouseWorkerUpdateRequest,
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
):
    """Update a warehouse worker user."""
    from uuid import UUID as _UUID

    user = (
        db.query(User)
        .filter(
            User.id == _UUID(worker_id),
            User.user_type == UserType.WAREHOUSE_WORKER,
            User.deleted_at.is_(None),
        )
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    # Check QR code uniqueness if changing
    new_qr = update_data.get("qr_code")
    if new_qr and new_qr != user.qr_code:
        existing_qr = db.query(User).filter(User.qr_code == new_qr).first()
        if existing_qr:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"QR code '{new_qr}' is already in use",
            )

    # Check email uniqueness if changing
    new_email = update_data.get("email")
    if new_email and new_email != user.email:
        existing_email = (
            db.query(User)
            .filter(User.email == new_email, User.deleted_at.is_(None))
            .first()
        )
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{new_email}' is already registered",
            )

    # Build display name if first/last name changed
    first = update_data.get("first_name", user.first_name)
    last = update_data.get("last_name", user.last_name)
    if "first_name" in update_data or "last_name" in update_data:
        update_data["display_name"] = f"{first} {last}"

    for key, value in update_data.items():
        if hasattr(user, key):
            setattr(user, key, value)

    db.commit()
    db.refresh(user)

    logger.info(
        "Worker updated",
        extra={
            "worker_id": str(user.id),
            "updated_by": str(current_user.id),
            "event": "worker_updated",
        },
    )

    return WarehouseWorkerResponse(**_user_to_response(user))


@router.delete(
    "/workers/{worker_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disable warehouse worker",
    description="Soft-delete (disable) a warehouse worker. Requires admin or org admin.",
)
async def delete_worker(
    worker_id: str,
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
):
    """Soft-delete (disable) a warehouse worker."""
    from uuid import UUID as _UUID

    user = (
        db.query(User)
        .filter(
            User.id == _UUID(worker_id),
            User.user_type == UserType.WAREHOUSE_WORKER,
            User.deleted_at.is_(None),
        )
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    user.is_active = False
    user.status = UserStatus.INACTIVE
    db.commit()

    logger.info(
        "Worker disabled",
        extra={
            "worker_id": str(user.id),
            "disabled_by": str(current_user.id),
            "event": "worker_disabled",
        },
    )

    return None


@router.post(
    "/workers/{worker_id}/regenerate-barcode",
    response_model=WarehouseWorkerResponse,
    summary="Regenerate QR code (legacy path)",
    description="Generate a new QR/barcode for a warehouse worker. Alias for /regenerate-qr.",
)
@router.post(
    "/workers/{worker_id}/regenerate-qr",
    response_model=WarehouseWorkerResponse,
    summary="Regenerate QR code",
    description="Generate a new QR code for a warehouse worker.",
)
async def regenerate_qr(
    worker_id: str,
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
):
    """Regenerate the QR code for a worker."""
    from uuid import UUID as _UUID

    user = (
        db.query(User)
        .filter(
            User.id == _UUID(worker_id),
            User.user_type == UserType.WAREHOUSE_WORKER,
            User.deleted_at.is_(None),
        )
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    # Generate new QR code
    new_qr = f"WRK-{secrets.token_hex(6).upper()}"
    user.qr_code = new_qr
    db.commit()
    db.refresh(user)

    logger.info(
        "Worker QR code regenerated",
        extra={
            "worker_id": str(user.id),
            "new_qr": new_qr,
            "regenerated_by": str(current_user.id),
            "event": "worker_qr_regenerated",
        },
    )

    return WarehouseWorkerResponse(**_user_to_response(user))
