"""Warehouse Workers Management — `users` is the single source of truth.

A warehouse worker is a `users` row with `user_type = warehouse_worker`,
assigned to warehouses via `warehouse_users` and to the organization via
`user_organization_roles`. This module exposes CRUD + batch import for
owner/admin/manager, including recoverable login credentials.
"""

import logging
import secrets
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.models.base import UserStatus, UserType
from app.models.role import Role, UserOrganizationRole
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

FALLBACK_EMAIL_DOMAIN = "warehouse.horizonsync.com"


async def require_worker_manager(
    current_user: CurrentUser = Depends(get_current_active_user),
) -> CurrentUser:
    if current_user.user_type in (UserType.SYSTEM_ADMIN, UserType.ORGANIZATION_ADMIN):
        return current_user
    if "warehouse.manage" in current_user.permissions:
        return current_user
    raise HTTPException(
        status_code=403,
        detail="Admin, org admin, or warehouse.manage permission required",
    )


def _get_org_id(current_user: CurrentUser, db: Session) -> str | None:
    uor = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == current_user.id,
            UserOrganizationRole.is_active == True,  # noqa: E712
        )
        .order_by(UserOrganizationRole.is_primary.desc())
        .first()
    )
    return str(uor.organization_id) if uor else None


VALID_WORKER_ROLES = ("warehouse_work_user", "wms_operator", "asn_coordinator")

# Legacy warehouse_users.role values still present from earlier seeds.
LEGACY_ROLE_MAP = {
    "operator": "warehouse_work_user",
    "manager": "wms_operator",
    "supervisor": "asn_coordinator",
}


def _wh_role_for(worker_role: str | None) -> str:
    """Normalize a worker role to one of the canonical worker role codes."""
    if worker_role in VALID_WORKER_ROLES:
        return worker_role
    if worker_role in LEGACY_ROLE_MAP:
        return LEGACY_ROLE_MAP[worker_role]
    return "warehouse_work_user"


def _user_row_to_dict(user: User, warehouse_id: str | None, wh_role: str | None) -> dict:
    return {
        "id": str(user.id),
        "email": user.email or "",
        "first_name": user.first_name,
        "last_name": user.last_name,
        "display_name": user.display_name or f"{user.first_name} {user.last_name}",
        "phone": user.phone or "",
        "user_type": "warehouse_worker",
        "role": _wh_role_for(wh_role),
        "status": user.status.value if user.status else "active",
        "is_active": bool(user.is_active),
        "qr_code": user.qr_code or "",
        "barcode": user.qr_code or "",
        "organization_id": "",
        "warehouse_id": warehouse_id or "",
        "login_username": user.login_username or "",
        "login_password": user.login_password or "",
        "employee_id": user.employee_id or "",
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login_at": user.last_login_at,
        "warehouse_assignments": [],
    }


def _primary_org_id(user: User, db: Session) -> str | None:
    uor = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == user.id,
            UserOrganizationRole.is_active == True,  # noqa: E712
        )
        .order_by(UserOrganizationRole.is_primary.desc())
        .first()
    )
    return str(uor.organization_id) if uor else None


def _warehouse_for(user_id: str, db: Session) -> tuple[str | None, str | None]:
    row = db.execute(
        sa_text(
            "SELECT warehouse_id, role FROM warehouse_users "
            "WHERE user_id=:u AND is_active=true "
            "ORDER BY is_primary DESC, created_at ASC LIMIT 1"
        ),
        {"u": user_id},
    ).fetchone()
    if row:
        return str(row.warehouse_id), str(row.role)
    return None, None


def _ensure_org_role(db: Session, user: User, org_id: str) -> None:
    role = (
        db.query(Role)
        .filter(Role.code == "warehouse_work_user", Role.is_active == True)  # noqa: E712
        .first()
    )
    if not role:
        return
    exists = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == user.id,
            UserOrganizationRole.organization_id == org_id,
            UserOrganizationRole.role_id == role.id,
        )
        .first()
    )
    if not exists:
        db.add(
            UserOrganizationRole(
                user_id=user.id,
                organization_id=org_id,
                role_id=role.id,
                is_primary=True,
                is_active=True,
                status="active",
            )
        )


def _ensure_warehouse_assignment(db: Session, user: User, org_id: str, warehouse_ids: list[str], role: str) -> None:
    wh_role = _wh_role_for(role)
    for wh in warehouse_ids:
        if not wh:
            continue
        exists = db.execute(
            sa_text("SELECT 1 FROM warehouse_users WHERE user_id=:u AND warehouse_id=:wh"),
            {"u": str(user.id), "wh": wh},
        ).fetchone()
        if exists:
            # Update the role on an existing assignment (e.g. a role-only
            # worker update) instead of ignoring it.
            db.execute(
                sa_text(
                    "UPDATE warehouse_users SET role=:r, updated_at=NOW() "
                    "WHERE user_id=:u AND warehouse_id=:wh"
                ),
                {"u": str(user.id), "wh": wh, "r": wh_role},
            )
        else:
            db.execute(
                sa_text(
                    "INSERT INTO warehouse_users (id, organization_id, user_id, "
                    "warehouse_id, role, is_primary, is_active, created_at, updated_at) "
                    "VALUES (:id,:org,:u,:wh,:r,false,true,NOW(),NOW())"
                ),
                {
                    "id": str(_uuid.uuid4()),
                    "org": org_id,
                    "u": str(user.id),
                    "wh": wh,
                    "r": wh_role,
                },
            )


def _set_password(user: User, password: str) -> None:
    user.login_password = password
    user.password_hash = hash_password(password)


@router.post("/workers", status_code=status.HTTP_201_CREATED)
async def create_worker(
    body: dict,
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
):
    org_id = body.get("organization_id") or _get_org_id(current_user, db)
    if not org_id:
        raise HTTPException(400, "organization_id required")

    fn, ln = body.get("first_name", ""), body.get("last_name", "")
    dn = body.get("display_name") or f"{fn} {ln}"
    qr = body.get("qr_code") or body.get("barcode") or f"WRK-{secrets.token_hex(6).upper()}"
    email = body.get("email") or f"{qr}@warehouse.local"
    password = body.get("password") or ""
    login_username = body.get("login_username")
    employee_id = body.get("employee_id")
    role = body.get("role") or body.get("warehouse_role") or "warehouse_work_user"

    wids = body.get("warehouse_ids") or []
    if body.get("warehouse_id") and body["warehouse_id"] not in wids:
        wids = [body["warehouse_id"]] + wids

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, f"Email {email} already exists")
    if db.query(User).filter(User.qr_code == qr).first():
        raise HTTPException(409, f"QR code {qr} already in use")
    if login_username and db.query(User).filter(User.login_username == login_username).first():
        raise HTTPException(409, f"Login username {login_username} already in use")

    user = User(
        email=email,
        password_hash=hash_password(password or secrets.token_urlsafe(16)),
        first_name=fn,
        last_name=ln,
        display_name=dn,
        phone=body.get("phone") or "",
        user_type=UserType.WAREHOUSE_WORKER,
        status=UserStatus.ACTIVE,
        is_active=True,
        email_verified=True,
        qr_code=qr,
        employee_id=employee_id,
        login_username=login_username,
        login_password=password or None,
    )
    db.add(user)
    db.flush()

    _ensure_org_role(db, user, org_id)
    _ensure_warehouse_assignment(db, user, org_id, wids, role)
    db.commit()
    db.refresh(user)

    wh_id, wh_role = _warehouse_for(str(user.id), db)
    d = _user_row_to_dict(user, wh_id, wh_role)
    d["organization_id"] = _primary_org_id(user, db) or ""
    return d


@router.get("/workers")
async def list_workers(
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    user_type: str | None = Query(None),
    warehouse_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
):
    org_id = _get_org_id(current_user, db)
    where = ["u.user_type = 'warehouse_worker'", "u.deleted_at IS NULL"]
    p: dict = {}
    if org_id and current_user.user_type != UserType.SYSTEM_ADMIN:
        where.append(
            "u.id IN (SELECT user_id FROM user_organization_roles "
            "WHERE organization_id=:org AND is_active=true)"
        )
        p["org"] = org_id
    if warehouse_id:
        where.append(
            "u.id IN (SELECT user_id FROM warehouse_users WHERE warehouse_id=:wh AND is_active=true)"
        )
        p["wh"] = warehouse_id
    if search:
        where.append(
            "(u.first_name ILIKE :s OR u.last_name ILIKE :s OR u.email ILIKE :s "
            "OR u.qr_code ILIKE :s OR u.login_username ILIKE :s)"
        )
        p["s"] = f"%{search}%"
    if status_filter == "active":
        where.append("u.is_active=true")
    elif status_filter == "inactive":
        where.append("u.is_active=false")

    wc = " AND ".join(where)
    total = db.execute(
        sa_text(f"SELECT count(*) FROM users u WHERE {wc}"), p
    ).scalar()
    rows = db.execute(
        sa_text(
            f"SELECT u.id FROM users u WHERE {wc} ORDER BY u.first_name, u.last_name "
            "LIMIT :lim OFFSET :off"
        ),
        {**p, "lim": page_size, "off": (page - 1) * page_size},
    ).fetchall()

    workers = []
    for r in rows:
        user = db.get(User, str(r.id))
        if not user:
            continue
        wh_id, wh_role = _warehouse_for(str(user.id), db)
        d = _user_row_to_dict(user, wh_id, wh_role)
        d["organization_id"] = _primary_org_id(user, db) or ""
        workers.append(d)

    return {
        "workers": workers,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max((total + page_size - 1) // page_size, 0) if page_size else 0,
    }


@router.get("/workers/{worker_id}")
async def get_worker(
    worker_id: str,
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
):
    user = db.get(User, worker_id)
    if not user or user.user_type != UserType.WAREHOUSE_WORKER:
        raise HTTPException(404, "Worker not found")
    wh_id, wh_role = _warehouse_for(str(user.id), db)
    d = _user_row_to_dict(user, wh_id, wh_role)
    d["organization_id"] = _primary_org_id(user, db) or ""
    return d


@router.patch("/workers/{worker_id}")
async def update_worker(
    worker_id: str,
    body: dict,
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
):
    user = db.get(User, worker_id)
    if not user or user.user_type != UserType.WAREHOUSE_WORKER:
        raise HTTPException(404, "Worker not found")

    for f in [
        "first_name",
        "last_name",
        "display_name",
        "phone",
        "employee_id",
        "login_username",
    ]:
        if f in body and body[f] is not None:
            setattr(user, f, body[f])

    if "email" in body and body["email"] is not None:
        user.email = body["email"]
    if "qr_code" in body and body["qr_code"] is not None:
        user.qr_code = body["qr_code"]
    elif "barcode" in body and body["barcode"] is not None:
        user.qr_code = body["barcode"]
    if "is_active" in body and body["is_active"] is not None:
        user.is_active = bool(body["is_active"])
        user.status = UserStatus.ACTIVE if body["is_active"] else UserStatus.SUSPENDED

    password = body.get("password")
    if password:
        _set_password(user, password)

    role = body.get("role") or body.get("warehouse_role")
    if body.get("warehouse_id") or role:
        wh = body.get("warehouse_id") or _warehouse_for(str(user.id), db)[0]
        if wh:
            _ensure_warehouse_assignment(
                db,
                user,
                _primary_org_id(user, db) or "",
                [str(wh)],
                role or "warehouse_work_user",
            )

    db.commit()
    db.refresh(user)
    wh_id, wh_role = _warehouse_for(str(user.id), db)
    d = _user_row_to_dict(user, wh_id, wh_role)
    d["organization_id"] = _primary_org_id(user, db) or ""
    return d


@router.delete("/workers/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_worker(
    worker_id: str,
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
):
    user = db.get(User, worker_id)
    if not user or user.user_type != UserType.WAREHOUSE_WORKER:
        raise HTTPException(404, "Worker not found")
    user.is_active = False
    user.status = UserStatus.SUSPENDED
    db.commit()
    return None


@router.post("/workers/import", status_code=status.HTTP_200_OK)
async def import_workers(
    body: dict,
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
):
    """Batch-create workers in a single transaction with per-row results."""
    org_id = body.get("organization_id") or _get_org_id(current_user, db)
    if not org_id:
        raise HTTPException(400, "organization_id required")

    workers = body.get("workers") or []
    created = 0
    failed = 0
    errors: list[dict] = []

    for idx, item in enumerate(workers):
        try:
            await create_worker(
                {**item, "organization_id": item.get("organization_id") or org_id},
                current_user=current_user,
                db=db,
            )
            created += 1
        except HTTPException as exc:
            db.rollback()
            failed += 1
            errors.append({"row": idx + 1, "error": exc.detail})
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            failed += 1
            errors.append({"row": idx + 1, "error": str(exc)})

    return {
        "created": created,
        "failed": failed,
        "total": len(workers),
        "errors": errors,
    }

