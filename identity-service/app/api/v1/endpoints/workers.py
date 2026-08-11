"""Warehouse Workers Management — reads/writes wms_workers directly (single source of truth)."""

import logging
import secrets
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

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
    db.commit()
    row = db.execute(
        sa_text("SELECT * FROM wms_workers WHERE id=:id"), {"id": eid}
    ).fetchone()
    return _worker_row_to_dict(row)


@router.get("/workers")
async def list_workers(
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    user_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_worker_manager),
    db: Session = Depends(get_db),
):
    org_id = _get_org_id(current_user, db)
    where = ["1=1"]
    p: dict = {}
    if current_user.user_type != UserType.SYSTEM_ADMIN and org_id:
        where.append("w.organization_id=:org")
        p["org"] = org_id
    if search:
        where.append(
            "(w.first_name ILIKE :s OR w.last_name ILIKE :s OR w.email ILIKE :s OR w.barcode ILIKE :s)"
        )
        p["s"] = f"%{search}%"
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
        sa_text("SELECT id FROM wms_workers WHERE id=:id"), {"id": worker_id}
    ).fetchone()
    if not row:
        raise HTTPException(404, "Worker not found")
    db.execute(
        sa_text(
            "UPDATE wms_workers SET is_active=false, status='inactive', updated_at=NOW() WHERE id=:id"
        ),
        {"id": worker_id},
    )
    db.commit()
    return None
