"""Admin authentication endpoints for identity-service"""

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import get_db
from app.dependencies import CurrentUser, get_core_service_client, require_admin
from app.models.base import UserStatus, UserType
from app.models.role import Role, UserOrganizationRole
from app.models.user import User
from app.schemas.admin import (
    AdminProfileResponse,
    CreateWarehouseWorkerRequest,
    WarehouseWorkerResponse,
)
from app.services.core_service_client import CoreServiceClient

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/me",
    response_model=AdminProfileResponse,
    summary="Get admin profile",
    description="Get current admin user profile with permissions. Requires system_admin user_type.",
)
async def get_admin_me(
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminProfileResponse:
    """
    Return the authenticated admin's profile including organization_id and permissions.

    This is the authoritative source for admin identity in the admin portal.
    Only accessible to users with user_type == system_admin.
    """
    # Look up the admin's primary organization
    user_org_role = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == current_user.id,
            UserOrganizationRole.is_active == True,  # noqa: E712
        )
        .order_by(UserOrganizationRole.is_primary.desc())
        .first()
    )

    organization_id = None
    if user_org_role:
        organization_id = str(user_org_role.organization_id)

    return AdminProfileResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        display_name=current_user.display_name,
        user_type=current_user.user_type.value
        if current_user.user_type
        else "system_admin",
        organization_id=organization_id,
        permissions=current_user.permissions,
    )


@router.post(
    "/create-worker",
    response_model=WarehouseWorkerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a warehouse worker user",
    description="Admin creates a warehouse worker with QR code login. Requires system_admin user_type.",
)
async def create_warehouse_worker(
    body: CreateWarehouseWorkerRequest,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
    core_client: CoreServiceClient | None = Depends(get_core_service_client),
):
    """
    Create a new warehouse worker user for QR code login.

    The worker will:
    - Have user_type = warehouse_worker
    - Be assigned the warehouse_work_user role
    - Have a unique QR code for scanning-based login
    - Get a random secure password (they log in via QR, not password)
    - Be assigned to specified warehouses (if warehouse_ids provided)
    """
    # Auto-generate email from QR code if not provided (workers may not have email)
    worker_email = body.email if body.email else f"{body.qr_code}@warehouse.local"

    # Check if email already exists
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

    # Check if QR code already exists
    existing_qr = db.query(User).filter(User.qr_code == body.qr_code).first()
    if existing_qr:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"QR code {body.qr_code} is already in use",
        )

    # Find the warehouse_work_user role
    warehouse_role = (
        db.query(Role)
        .filter(Role.code == "warehouse_work_user", Role.is_active == True)  # noqa: E712
        .first()
    )
    if not warehouse_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="warehouse_work_user role not found. Run seed data first.",
        )

    # Create the user with a random password (they login via QR)
    random_password = secrets.token_urlsafe(16)
    user = User(
        email=worker_email,
        password_hash=hash_password(random_password),
        first_name=body.first_name,
        last_name=body.last_name,
        display_name=f"{body.first_name} {body.last_name}",
        phone=body.phone,
        user_type=UserType.WAREHOUSE_WORKER,
        status=UserStatus.ACTIVE,
        is_active=True,
        email_verified=True,  # Workers don't need email verification
        qr_code=body.qr_code,
    )
    db.add(user)
    db.flush()

    # Assign the warehouse_work_user role
    user_org_role = UserOrganizationRole(
        user_id=user.id,
        organization_id=body.organization_id,
        role_id=warehouse_role.id,
        is_primary=True,
        is_active=True,
        status="active",
    )
    db.add(user_org_role)
    db.commit()
    db.refresh(user)

    # Assign warehouse access if warehouse_ids provided
    warehouse_errors = []
    if body.warehouse_ids and core_client:
        for wh_id in body.warehouse_ids:
            try:
                await core_client.assign_user_to_warehouse(
                    user_id=user.id,
                    organization_id=body.organization_id,
                    warehouse_id=wh_id,
                    role=body.warehouse_role or "operator",
                )
                logger.info(
                    "Assigned worker to warehouse",
                    extra={
                        "user_id": str(user.id),
                        "warehouse_id": str(wh_id),
                        "role": body.warehouse_role or "operator",
                        "event": "worker_warehouse_assigned",
                    },
                )
            except Exception as exc:
                logger.error(
                    "Failed to assign worker to warehouse",
                    extra={
                        "user_id": str(user.id),
                        "warehouse_id": str(wh_id),
                        "error": str(exc),
                        "event": "worker_warehouse_assignment_failed",
                    },
                )
                warehouse_errors.append(str(wh_id))

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
        organization_id=str(body.organization_id),
        created_at=user.created_at,
        warehouse_assignments=(
            [str(wid) for wid in body.warehouse_ids]
            if body.warehouse_ids
            else []
        ),
    )
