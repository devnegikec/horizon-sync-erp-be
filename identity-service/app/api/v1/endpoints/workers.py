"""Warehouse Workers Management — `users` is the single source of truth.

A warehouse worker is a `users` row with `user_type = warehouse_worker`,
assigned to warehouses via `warehouse_users` and to the organization via
`user_organization_roles`. This module exposes CRUD + batch import for
owner/admin/manager, including recoverable login credentials.
"""

import logging
import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from app.core.authorization import has_permission
from app.core.error_handler import http_error
from app.core.security import hash_password
from app.database import get_db
from app.dependencies import (
    CurrentUser,
    get_core_service_client,
    get_current_active_user,
)
from app.models.base import UserStatus, UserType
from app.models.role import Role, UserOrganizationRole
from app.models.user import User
from app.services.core_service_client import CoreServiceClient

logger = logging.getLogger(__name__)
router = APIRouter()

FALLBACK_EMAIL_DOMAIN = "warehouse.horizonsync.com"


async def require_worker_manager(
    current_user: CurrentUser = Depends(get_current_active_user),
) -> CurrentUser:
    if current_user.user_type in (UserType.SYSTEM_ADMIN, UserType.ORGANIZATION_ADMIN):
        return current_user
    # Wildcard-aware check: grants exact 'warehouse.manage', resource wildcard
    # 'warehouse.*', or full wildcard '*.*' (organization owner).
    if has_permission(current_user.permissions, "warehouse.manage"):
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


# Values accepted by the ``warehouse_users.role`` enum column (see core-service
# migrations). Canonical worker role codes must be mapped back to these before
# writing to the DB.
WAREHOUSE_ROLE_ENUM_VALUES = ("operator", "manager", "supervisor", "coordinator")

CANONICAL_TO_WAREHOUSE_ROLE = {
    "warehouse_work_user": "operator",
    "wms_operator": "manager",
    "asn_coordinator": "supervisor",
}


def _warehouse_enum_role(worker_role: str | None) -> str:
    """Map a worker role to a valid ``warehouse_users.role`` enum value."""
    if worker_role in WAREHOUSE_ROLE_ENUM_VALUES:
        return worker_role
    return CANONICAL_TO_WAREHOUSE_ROLE.get(worker_role, "operator")


def _user_row_to_dict(
    user: User, warehouse_id: str | None, wh_role: str | None
) -> dict:
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


async def _get_core_client() -> CoreServiceClient:
    """Core Service client — the only supported path to `warehouse_users`.

    The ``warehouse_users`` table lives in the Core Service database, so this
    service must never query it directly.
    """
    client = get_core_service_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Core Service is not configured (CORE_SERVICE_URL)",
        )
    return client


async def _warehouse_for(
    client: CoreServiceClient, user_id: str, organization_id: str | None
) -> tuple[str | None, str | None]:
    """Read a worker's primary warehouse assignment from Core Service.

    Returns ``(warehouse_id, role)`` or ``(None, None)``. Read failures degrade
    to "no assignment" (logged) so a listing can still be served.
    """
    try:
        rows = await client.get_warehouse_assignments(
            organization_id=organization_id, user_ids=[user_id]
        )
    except httpx.HTTPError as exc:
        logger.warning(
            "[workers] could not read warehouse assignment user=%s: %s", user_id, exc
        )
        return None, None
    if not rows:
        return None, None
    row = rows[0]
    return (row.get("warehouse_id") or None), row.get("role")


async def _assign_warehouses(
    client: CoreServiceClient,
    *,
    user_id: str,
    organization_id: str | None,
    warehouse_ids: list[str],
    role: str | None,
    is_primary: bool = False,
) -> None:
    """Create or refresh a worker's warehouse assignments in Core Service.

    Deliberately strict: if Core Service cannot be reached this raises, so the
    caller's transaction is aborted and we never persist a worker that has no
    warehouse assignment.
    """
    targets = [str(w) for w in warehouse_ids if w]
    if not targets:
        return
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_id is required to assign warehouses",
        )

    enum_role = _warehouse_enum_role(role)
    for warehouse in targets:
        try:
            await client.assign_user_to_warehouse(
                user_id=user_id,
                organization_id=organization_id,
                warehouse_id=warehouse,
                role=enum_role,
                is_primary=is_primary,
            )
        except httpx.HTTPError as exc:
            response = getattr(exc, "response", None)
            detail = response.text if response is not None else ""
            logger.error(
                "[workers] warehouse assignment failed user=%s warehouse=%s: %s %s",
                user_id,
                warehouse,
                exc,
                detail,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    f"Failed to assign warehouse {warehouse} in Core Service: "
                    f"{exc}. {detail}"
                ).strip(),
            ) from exc


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


def _set_password(user: User, password: str) -> None:
    user.login_password = password
    user.password_hash = hash_password(password)


def _login_username_taken_in_org(
    db: Session,
    org_id: str | None,
    login_username: str,
    exclude_user_id=None,
) -> bool:
    """True if another user in the same organization already uses this username.

    Worker ``login_username`` values are unique per organization, not globally —
    two workers in different organizations may share the same username. Without
    an organization context this falls back to the legacy global check.
    """
    if not org_id:
        q = db.query(User).filter(User.login_username == login_username)
    else:
        q = (
            db.query(User)
            .join(UserOrganizationRole, UserOrganizationRole.user_id == User.id)
            .filter(
                UserOrganizationRole.organization_id == org_id,
                UserOrganizationRole.is_active == True,  # noqa: E712
                User.login_username == login_username,
            )
        )
    if exclude_user_id is not None:
        q = q.filter(User.id != exclude_user_id)
    return q.first() is not None
async def _worker_ids_for_warehouse(
    client: CoreServiceClient | None,
    warehouse_id: str,
    organization_id: str | None,
) -> list[str]:
    """Resolve the worker ids assigned to a warehouse.

    Core Service owns ``warehouse_users``, so the id set is read there and then
    applied as a local filter — filtering after pagination would be wrong.
    """
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Core Service is not configured (CORE_SERVICE_URL)",
        )
    assignments = await client.get_warehouse_assignments(
        organization_id=organization_id, warehouse_id=warehouse_id
    )
    return sorted({str(a["user_id"]) for a in assignments if a.get("user_id")})


async def _assignments_for_users(
    client: CoreServiceClient | None,
    organization_id: str | None,
    user_ids: list[str],
) -> dict[str, dict]:
    """Bulk-read assignments for a page of workers, keyed by user id.

    One call per page instead of one per worker. Enrichment failures are logged
    and degrade to "no assignment" rather than failing the whole listing.
    """
    if client is None or not user_ids:
        return {}
    try:
        rows = await client.get_warehouse_assignments(
            organization_id=organization_id, user_ids=user_ids
        )
    except httpx.HTTPError as exc:
        logger.warning("[workers] warehouse enrichment failed: %s", exc)
        return {}

    by_user: dict[str, dict] = {}
    for row in rows:
        # Primary rows come first, so keep the first seen per user.
        by_user.setdefault(str(row["user_id"]), row)
    return by_user


async def _sync_worker_assignment(
    client: CoreServiceClient,
    user: User,
    organization_id: str | None,
    body: dict,
    role: str | None,
) -> None:
    """Re-point or re-role a worker's assignment when a PATCH asks for it."""
    warehouse_id = body.get("warehouse_id")
    if not warehouse_id:
        warehouse_id = (await _warehouse_for(client, str(user.id), organization_id))[0]
    if not warehouse_id:
        return
    await _assign_warehouses(
        client,
        user_id=str(user.id),
        organization_id=organization_id,
        warehouse_ids=[str(warehouse_id)],
        role=role or "warehouse_work_user",
    )


WORKER_TEXT_FIELDS = (
    "first_name",
    "last_name",
    "display_name",
    "phone",
    "employee_id",
    "login_username",
)


def _apply_worker_fields(user: User, body: dict) -> None:
    """Apply the scalar/reference field updates from a PATCH body."""
    for field in WORKER_TEXT_FIELDS:
        if body.get(field) is not None:
            setattr(user, field, body[field])

    if body.get("email") is not None:
        user.email = body["email"]

    if body.get("qr_code") is not None:
        user.qr_code = body["qr_code"]
    elif body.get("barcode") is not None:
        user.qr_code = body["barcode"]

    if body.get("is_active") is not None:
        user.is_active = bool(body["is_active"])
        user.status = UserStatus.ACTIVE if user.is_active else UserStatus.SUSPENDED


def _status_clause(status_filter: str | None) -> str | None:
    """Map the ``status`` query parameter onto a SQL predicate."""
    if status_filter == "active":
        return "u.is_active=true"
    if status_filter == "inactive":
        return "u.is_active=false"
    return None


def _empty_worker_page(page: int, page_size: int) -> dict:
    """Empty result page, used when a warehouse filter matches no workers."""
    return {
        "workers": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "total_pages": 0,
    }


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
    qr = (
        body.get("qr_code")
        or body.get("barcode")
        or f"WRK-{secrets.token_hex(6).upper()}"
    )
    email = body.get("email") or f"{qr}@warehouse.local"
    password = body.get("password") or ""
    login_username = body.get("login_username")
    employee_id = body.get("employee_id")
    role = body.get("role") or body.get("warehouse_role") or "warehouse_work_user"

    wids = body.get("warehouse_ids") or []
    if body.get("warehouse_id") and body["warehouse_id"] not in wids:
        wids = [body["warehouse_id"]] + wids

    if db.query(User).filter(User.email == email).first():
        raise http_error(409, f"Email {email} already exists", code="EMAIL_TAKEN")
    if db.query(User).filter(User.qr_code == qr).first():
        raise http_error(409, f"QR code {qr} already in use", code="QR_CODE_TAKEN")
    if login_username and _login_username_taken_in_org(db, org_id, login_username):
        raise http_error(
            409,
            f"Login username {login_username} already in use",
            code="LOGIN_USERNAME_TAKEN",
        )

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

    # warehouse_users is owned by Core Service, so assignments go through its
    # internal API. A failure here aborts the transaction, so we never persist a
    # worker that has no warehouse assignment.
    client = await _get_core_client()
    await _assign_warehouses(
        client,
        user_id=str(user.id),
        organization_id=org_id,
        warehouse_ids=wids,
        role=role,
    )

    db.commit()
    db.refresh(user)

    wh_id, wh_role = await _warehouse_for(client, str(user.id), org_id)
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
    client = get_core_service_client()
    where = ["u.user_type = 'warehouse_worker'", "u.deleted_at IS NULL"]
    p: dict = {}
    if org_id and current_user.user_type != UserType.SYSTEM_ADMIN:
        where.append(
            "u.id IN (SELECT user_id FROM user_organization_roles "
            "WHERE organization_id=:org AND is_active=true)"
        )
        p["org"] = org_id
    if warehouse_id:
        # warehouse_users lives in Core Service, so resolve the assigned worker
        # ids there before filtering/paginating locally.
        worker_ids = await _worker_ids_for_warehouse(client, warehouse_id, org_id)
        if not worker_ids:
            return _empty_worker_page(page, page_size)
        where.append("u.id = ANY(CAST(:wh_users AS uuid[]))")
        p["wh_users"] = worker_ids
    if search:
        where.append(
            "(u.first_name ILIKE :s OR u.last_name ILIKE :s OR u.email ILIKE :s "
            "OR u.qr_code ILIKE :s OR u.login_username ILIKE :s)"
        )
        p["s"] = f"%{search}%"
    status_predicate = _status_clause(status_filter)
    if status_predicate:
        where.append(status_predicate)

    wc = " AND ".join(where)
    total = db.execute(sa_text(f"SELECT count(*) FROM users u WHERE {wc}"), p).scalar()
    rows = db.execute(
        sa_text(
            f"SELECT u.id FROM users u WHERE {wc} ORDER BY u.first_name, u.last_name "
            "LIMIT :lim OFFSET :off"
        ),
        {**p, "lim": page_size, "off": (page - 1) * page_size},
    ).fetchall()

    workers = []
    assignment_by_user = await _assignments_for_users(
        client, org_id, [str(r.id) for r in rows]
    )

    for r in rows:
        user = db.get(User, str(r.id))
        if not user:
            continue
        assignment = assignment_by_user.get(str(user.id))
        wh_id = str(assignment["warehouse_id"]) if assignment else None
        wh_role = assignment.get("role") if assignment else None
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
    client = await _get_core_client()
    wh_id, wh_role = await _warehouse_for(
        client, str(user.id), _primary_org_id(user, db)
    )
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
    ]:
        if f in body and body[f] is not None:
            setattr(user, f, body[f])

    if "login_username" in body and body["login_username"] is not None:
        new_lu = body["login_username"]
        if new_lu and _login_username_taken_in_org(
            db, _primary_org_id(user, db), new_lu, exclude_user_id=user.id
        ):
            raise http_error(
                409,
                f"Login username {new_lu} already in use",
                code="LOGIN_USERNAME_TAKEN",
            )
        user.login_username = new_lu

    if "email" in body and body["email"] is not None:
        user.email = body["email"]
    if "qr_code" in body and body["qr_code"] is not None:
        user.qr_code = body["qr_code"]
    elif "barcode" in body and body["barcode"] is not None:
        user.qr_code = body["barcode"]
    if "is_active" in body and body["is_active"] is not None:
        user.is_active = bool(body["is_active"])
        user.status = UserStatus.ACTIVE if body["is_active"] else UserStatus.SUSPENDED
    _apply_worker_fields(user, body)

    password = body.get("password")
    if password:
        _set_password(user, password)

    role = body.get("role") or body.get("warehouse_role")
    org_id = _primary_org_id(user, db)
    client = await _get_core_client()
    if body.get("warehouse_id") or role:
        await _sync_worker_assignment(client, user, org_id, body, role)

    db.commit()
    db.refresh(user)
    wh_id, wh_role = await _warehouse_for(client, str(user.id), org_id)
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
            detail = exc.detail
            if isinstance(detail, dict):
                detail = detail.get("message") or detail.get("code") or "Unknown error"
            errors.append({"row": idx + 1, "error": detail})
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
