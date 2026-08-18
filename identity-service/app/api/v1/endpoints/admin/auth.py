"""Admin authentication endpoints for identity-service"""

import logging
import secrets
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from app.api.v1.endpoints.workers import require_worker_manager
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
    current_user: CurrentUser = Depends(require_worker_manager),
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
    org_id = body.organization_id

    # Resolve QR code
    qr_code = body.qr_code
    if not qr_code:
        if body.employee_id:
            qr_code = body.employee_id
        else:
            qr_code = f"WRK-{secrets.token_hex(6).upper()}"

    # Auto-generate email from QR code if not provided
    worker_email = body.email if body.email else f"{qr_code}@warehouse.local"

    # Resolve warehouse_ids
    warehouse_ids: list = []
    if body.warehouse_ids:
        warehouse_ids = list(body.warehouse_ids)
    if body.warehouse_id and body.warehouse_id not in warehouse_ids:
        warehouse_ids.append(body.warehouse_id)

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
    existing_qr = db.query(User).filter(User.qr_code == qr_code).first()
    if existing_qr:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"QR code {qr_code} is already in use",
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
        email_verified=True,
        qr_code=qr_code,
    )
    db.add(user)
    db.flush()

    # Assign the warehouse_work_user role
    user_org_role = UserOrganizationRole(
        user_id=user.id,
        organization_id=org_id,
        role_id=warehouse_role.id,
        is_primary=True,
        is_active=True,
        status="active",
    )
    db.add(user_org_role)
    db.commit()
    db.refresh(user)

    # Mirror to wms_workers (inventory app's worker list / printed QR source).
    # Only possible when a warehouse is assigned (warehouse_id is NOT NULL).
    if warehouse_ids:
        try:
            mirror_exists = db.execute(
                sa_text("SELECT 1 FROM wms_workers WHERE barcode=:bc"),
                {"bc": qr_code},
            ).fetchone()
            if not mirror_exists:
                db.execute(
                    sa_text(
                        "INSERT INTO wms_workers (id,organization_id,warehouse_id,"
                        "first_name,last_name,display_name,email,phone,barcode,"
                        "employee_id,login_username,role,status,is_active,created_at,"
                        "updated_at) VALUES (:id,:org,:wh,:fn,:ln,:dn,:em,:ph,:bc,"
                        ":eid,:lu,:role,'active',true,NOW(),NOW())"
                    ),
                    {
                        "id": str(_uuid.uuid4()),
                        "org": str(org_id),
                        "wh": str(warehouse_ids[0]),
                        "fn": body.first_name,
                        "ln": body.last_name,
                        "dn": user.display_name,
                        "em": worker_email,
                        "ph": body.phone or "",
                        "bc": qr_code,
                        "eid": body.employee_id,
                        "lu": body.login_username,
                        "role": "warehouse_worker",
                    },
                )
                db.commit()
        except Exception as exc:
            logger.warning("Failed to mirror worker to wms_workers: %s", exc)

    # Assign warehouse access if warehouse_ids provided
    warehouse_errors = []
    if warehouse_ids and core_client:
        for wh_id in warehouse_ids:
            try:
                await core_client.assign_user_to_warehouse(
                    user_id=user.id,
                    organization_id=org_id,
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
        organization_id=str(org_id),
        created_at=user.created_at,
        warehouse_assignments=(
            [str(wid) for wid in warehouse_ids] if body.warehouse_ids else []
        ),
    )
