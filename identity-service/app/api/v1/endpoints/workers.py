"""Warehouse Workers Management — reads/writes wms_workers directly (single source of truth)."""

import logging
import secrets
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.models.base import UserType
from app.models.role import UserOrganizationRole

logger = logging.getLogger(__name__)
router = APIRouter()


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
            UserOrganizationRole.is_active == True,
        )
        .order_by(UserOrganizationRole.is_primary.desc())
        .first()
    )
    return str(uor.organization_id) if uor else None


def _worker_row_to_dict(row) -> dict:
    return {
        "id": str(row.id),
        "email": row.email or "",
        "first_name": row.first_name,
        "last_name": row.last_name,
        "display_name": row.display_name or f"{row.first_name} {row.last_name}",
        "phone": row.phone or "",
        "user_type": "warehouse_worker",
        "role": row.role or "warehouse_worker",
        "status": row.status or "active",
        "is_active": bool(row.is_active),
        "qr_code": row.barcode or "",
        "organization_id": str(row.organization_id),
        "login_username": getattr(row, "login_username", None) or "",
        "employee_id": getattr(row, "employee_id", None) or "",
        "created_at": row.created_at,
        "last_login_at": getattr(row, "last_login_at", None),
        "warehouse_assignments": [],
    }


# Valid, non-reserved domain — `.local` is rejected by Pydantic EmailStr.
FALLBACK_EMAIL_DOMAIN = "warehouse.horizonsync.com"


def _wh_role_for(worker_role: str | None) -> str:
    if worker_role in ("warehouse_supervisor", "supervisor"):
        return "supervisor"
    if worker_role == "manager":
        return "manager"
    return "operator"


def _ensure_auth_user(
    db: Session,
    *,
    barcode: str,
    org_id: str | None,
    warehouse_ids: list[str],
    role: str | None,
    email: str | None,
    first_name: str,
    last_name: str,
    display_name: str,
    phone: str | None,
    is_active: bool = True,
) -> None:
    """Create/keep in sync the identity `users` row, org role and warehouse
    assignment for a wms_worker, so mobile QR login and warehouse loading work."""
    if not barcode:
        return

    # 1. Find or create the users row by qr_code
    row = db.execute(
        sa_text("SELECT id FROM users WHERE qr_code=:q"), {"q": barcode}
    ).fetchone()
    if row:
        uid = str(row.id)
        db.execute(
            sa_text(
                "UPDATE users SET first_name=:fn, last_name=:ln, display_name=:dn, "
                "phone=:ph, is_active=:ia, updated_at=NOW() WHERE id=:id"
            ),
            {
                "fn": first_name,
                "ln": last_name,
                "dn": display_name,
                "ph": phone,
                "ia": is_active,
                "id": uid,
            },
        )
    else:
        uid = str(_uuid.uuid4())
        em = email or f"{barcode}@{FALLBACK_EMAIL_DOMAIN}"
        if db.execute(
            sa_text("SELECT 1 FROM users WHERE email=:e"), {"e": em}
        ).fetchone():
            em = f"{barcode}.{_uuid.uuid4().hex[:6]}@{FALLBACK_EMAIL_DOMAIN}"
        pw = hash_password(secrets.token_urlsafe(16))
        db.execute(
            sa_text(
                "INSERT INTO users (id, email, password_hash, first_name, last_name, "
                "display_name, phone, user_type, status, is_active, email_verified, "
                "qr_code, preferences, timezone, language, created_at, updated_at) "
                "VALUES (:id,:em,:pw,:fn,:ln,:dn,:ph,'warehouse_worker','active',:ia,"
                "true,:q,'{}','UTC','en',NOW(),NOW())"
            ),
            {
                "id": uid,
                "em": em,
                "pw": pw,
                "fn": first_name,
                "ln": last_name,
                "dn": display_name,
                "ph": phone,
                "ia": is_active,
                "q": barcode,
            },
        )

    # 2. Ensure org role assignment
    if org_id:
        role_row = db.execute(
            sa_text(
                "SELECT id FROM roles WHERE code='warehouse_work_user' AND "
                "organization_id=:org AND is_active=true LIMIT 1"
            ),
            {"org": org_id},
        ).fetchone()
        if role_row:
            role_id = str(role_row.id)
            exists = db.execute(
                sa_text(
                    "SELECT 1 FROM user_organization_roles WHERE user_id=:u AND "
                    "organization_id=:org AND role_id=:r"
                ),
                {"u": uid, "org": org_id, "r": role_id},
            ).fetchone()
            if not exists:
                db.execute(
                    sa_text(
                        "INSERT INTO user_organization_roles (id, user_id, organization_id, "
                        "role_id, is_primary, is_active, status, created_at, updated_at) "
                        "VALUES (:id,:u,:org,:r,true,true,'active',NOW(),NOW())"
                    ),
                    {"id": str(_uuid.uuid4()), "u": uid, "org": org_id, "r": role_id},
                )

    # 3. Ensure warehouse assignments
    wh_role = _wh_role_for(role)
    for wh in warehouse_ids:
        if not wh:
            continue
        exists = db.execute(
            sa_text(
                "SELECT 1 FROM warehouse_users WHERE user_id=:u AND warehouse_id=:wh"
            ),
            {"u": uid, "wh": wh},
        ).fetchone()
        if not exists:
            db.execute(
                sa_text(
                    "INSERT INTO warehouse_users (id, organization_id, user_id, "
                    "warehouse_id, role, is_primary, is_active, created_at, updated_at) "
                    "VALUES (:id,:org,:u,:wh,:r,false,true,NOW(),NOW())"
                ),
                {
                    "id": str(_uuid.uuid4()),
                    "org": org_id,
                    "u": uid,
                    "wh": wh,
                    "r": wh_role,
                },
            )


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
    email = body.get("email") or f"worker-{secrets.token_hex(4)}@warehouse.local"
    qr = body.get("qr_code") or f"WRK-{secrets.token_hex(6).upper()}"
    role = body.get("role") or body.get("warehouse_role") or "warehouse_worker"
    wids = body.get("warehouse_ids") or []
    if body.get("warehouse_id") and body["warehouse_id"] not in wids:
        wids = [body["warehouse_id"]] + wids
    wid = wids[0] if wids else None

    ex = db.execute(
        sa_text("SELECT id FROM wms_workers WHERE barcode=:bc"), {"bc": qr}
    ).fetchone()
    if ex:
        raise HTTPException(409, f"QR code {qr} already in use")

    eid = str(_uuid.uuid4())
    db.execute(
        sa_text(
            "INSERT INTO wms_workers (id,organization_id,warehouse_id,first_name,last_name,display_name,email,phone,barcode,employee_id,login_username,role,status,is_active,created_at,updated_at) "
            "VALUES (:id,:org,:wh,:fn,:ln,:dn,:em,:ph,:bc,:eid,:lu,:role,'active',true,NOW(),NOW())"
        ),
        {
            "id": eid,
            "org": org_id,
            "wh": wid,
            "fn": fn,
            "ln": ln,
            "dn": dn,
            "em": email,
            "ph": body.get("phone") or "",
            "bc": qr,
            "eid": body.get("employee_id"),
            "lu": body.get("login_username"),
            "role": role,
        },
    )
    _ensure_auth_user(
        db,
        barcode=qr,
        org_id=org_id,
        warehouse_ids=wids,
        role=role,
        email=email,
        first_name=fn,
        last_name=ln,
        display_name=dn,
        phone=body.get("phone") or "",
        is_active=True,
    )
    db.commit()
    row = db.execute(
        sa_text("SELECT * FROM wms_workers WHERE id=:id"), {"id": eid}
    ).fetchone()
    return _worker_row_to_dict(row)


@router.get("/workers")
async def list_workers(search: str|None=Query(None), status_filter: str|None=Query(None,alias="status"),
                       user_type: str|None=Query(None), warehouse_id: str|None=Query(None),
                       page: int=Query(1,ge=1), page_size: int=Query(20,ge=1,le=100),
                       current_user: CurrentUser=Depends(require_worker_manager), db: Session=Depends(get_db)):
    org_id = _get_org_id(current_user, db)
    where = ["1=1"]
    p: dict = {}
    if current_user.user_type != UserType.SYSTEM_ADMIN and org_id:
        where.append("w.organization_id=:org"); p["org"] = org_id
    if warehouse_id:
        where.append("w.warehouse_id=:wh"); p["wh"] = warehouse_id
    if search:
        where.append(
            "(w.first_name ILIKE :s OR w.last_name ILIKE :s OR w.email ILIKE :s OR w.barcode ILIKE :s)"
        )
        p["s"] = f"%{search}%"
    if warehouse_id:
        where.append("w.warehouse_id=:wh")
        p["wh"] = warehouse_id
    if status_filter == "active":
        where.append("w.is_active=true")
    elif status_filter == "inactive":
        where.append("w.is_active=false")
    wc = " AND ".join(where)
    total = db.execute(
        sa_text(f"SELECT count(*) FROM wms_workers w WHERE {wc}"), p
    ).scalar()
    rows = db.execute(
        sa_text(
            f"SELECT w.* FROM wms_workers w WHERE {wc} ORDER BY w.first_name,w.last_name LIMIT :lim OFFSET :off"
        ),
        {**p, "lim": page_size, "off": (page - 1) * page_size},
    ).fetchall()
    return {
        "workers": [_worker_row_to_dict(r) for r in rows],
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
    row = db.execute(
        sa_text("SELECT * FROM wms_workers WHERE id=:id"), {"id": worker_id}
    ).fetchone()
    if not row:
        raise HTTPException(404, "Worker not found")
    return _worker_row_to_dict(row)


@router.patch("/workers/{worker_id}")
async def update_worker(
    worker_id: str,
    body: dict,
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
):
    row = db.execute(
        sa_text("SELECT * FROM wms_workers WHERE id=:id"), {"id": worker_id}
    ).fetchone()
    if not row:
        raise HTTPException(404, "Worker not found")
    old_barcode = row.barcode
    updates, params = [], {"id": worker_id}
    for f in [
        "first_name",
        "last_name",
        "display_name",
        "email",
        "phone",
        "barcode",
        "employee_id",
        "login_username",
        "role",
        "status",
    ]:
        if f in body and body[f] is not None:
            updates.append(f"{f}=:{f}")
            params[f] = body[f]
    if "is_active" in body and body["is_active"] is not None:
        updates.append("is_active=:ia")
        params["ia"] = body["is_active"]
    if "warehouse_id" in body and body["warehouse_id"] is not None:
        updates.append("warehouse_id=:wh")
        params["wh"] = body["warehouse_id"]
    if not updates:
        raise HTTPException(400, "No fields to update")
    updates.append("updated_at=NOW()")
    db.execute(
        sa_text(f"UPDATE wms_workers SET {', '.join(updates)} WHERE id=:id"), params
    )
    # Keep identity `users` row in sync (barcode/qr_code + active state)
    new_barcode = body.get("barcode") or old_barcode
    if new_barcode and new_barcode != old_barcode:
        db.execute(
            sa_text("UPDATE users SET qr_code=:nq, updated_at=NOW() WHERE qr_code=:oq"),
            {"nq": new_barcode, "oq": old_barcode},
        )
    if "is_active" in body and body["is_active"] is not None:
        db.execute(
            sa_text(
                "UPDATE users SET is_active=:ia, status=:st, updated_at=NOW() "
                "WHERE qr_code=:q"
            ),
            {
                "ia": bool(body["is_active"]),
                "st": "active" if body["is_active"] else "suspended",
                "q": new_barcode,
            },
        )
    if "email" in body and body["email"] is not None:
        db.execute(
            sa_text("UPDATE users SET email=:em, updated_at=NOW() WHERE qr_code=:q"),
            {"em": body["email"], "q": new_barcode},
        )
    db.commit()
    row = db.execute(
        sa_text("SELECT * FROM wms_workers WHERE id=:id"), {"id": worker_id}
    ).fetchone()
    return _worker_row_to_dict(row)


@router.delete("/workers/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_worker(
    worker_id: str,
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
):
    row = db.execute(
        sa_text("SELECT id, barcode FROM wms_workers WHERE id=:id"), {"id": worker_id}
    ).fetchone()
    if not row:
        raise HTTPException(404, "Worker not found")
    db.execute(
        sa_text(
            "UPDATE wms_workers SET is_active=false, status='inactive', updated_at=NOW() WHERE id=:id"
        ),
        {"id": worker_id},
    )
    if row.barcode:
        db.execute(
            sa_text(
                "UPDATE users SET is_active=false, status='suspended', updated_at=NOW() "
                "WHERE qr_code=:q"
            ),
            {"q": row.barcode},
        )
    db.commit()
    return None
