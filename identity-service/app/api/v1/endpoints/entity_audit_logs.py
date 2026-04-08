"""Entity audit log endpoints for identity-service CRUD tracking.

GET /entity-audit-logs  — paginated list with optional filters
"""

import logging
import math
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.models.entity_audit_log import EntityAuditLog
from app.models.user import User
from app.models.organization import Organization

router = APIRouter()
logger = logging.getLogger(__name__)


class AuditLogItem(BaseModel):
    id: UUID
    user_id: UUID | None = None
    organization_id: UUID | None = None
    action: str
    table_name: str
    record_id: UUID
    old_values: dict | None = None
    new_values: dict | None = None
    changed_fields: list[str] | None = None
    ip_address: str | None = None
    created_at: datetime | None = None
    # Resolved fields
    user_email: str | None = None
    user_name: str | None = None
    user_email_address: str | None = None
    organization_name: str | None = None

    class Config:
        from_attributes = True


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class AuditLogListResponse(BaseModel):
    audit_logs: list[AuditLogItem]
    pagination: PaginationMeta


def _resolve_users(db: Session, user_ids: set[UUID]) -> dict[UUID, dict]:
    if not user_ids:
        return {}
    users = db.query(User.id, User.first_name, User.last_name, User.email).filter(User.id.in_(user_ids)).all()
    result = {}
    for u in users:
        name = f"{u.first_name or ''} {u.last_name or ''}".strip()
        result[u.id] = {"name": name, "email": u.email}
    return result


def _resolve_orgs(db: Session, org_ids: set[UUID]) -> dict[UUID, str]:
    if not org_ids:
        return {}
    orgs = db.query(Organization.id, Organization.name).filter(Organization.id.in_(org_ids)).all()
    return {o.id: o.name for o in orgs}


def _resolve_user_orgs(db: Session, user_ids: set[UUID]) -> dict[UUID, UUID]:
    """Resolve user_id → primary organization_id from user_organization_roles."""
    if not user_ids:
        return {}
    from app.models.role import UserOrganizationRole
    roles = (
        db.query(UserOrganizationRole.user_id, UserOrganizationRole.organization_id)
        .filter(
            UserOrganizationRole.user_id.in_(user_ids),
            UserOrganizationRole.is_active == True,
            UserOrganizationRole.is_primary == True,
        )
        .all()
    )
    return {r.user_id: r.organization_id for r in roles}
    orgs = db.query(Organization.id, Organization.name).filter(Organization.id.in_(org_ids)).all()
    return {o.id: o.name for o in orgs}


@router.get("", response_model=AuditLogListResponse)
async def list_entity_audit_logs(
    organization_id: UUID | None = Query(None),
    table_name: str | None = Query(None),
    record_id: UUID | None = Query(None),
    user_id: UUID | None = Query(None),
    action: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("system_admin.reporting")),
) -> AuditLogListResponse:
    """Return paginated entity audit logs with resolved user/org names."""
    query = db.query(EntityAuditLog)

    if organization_id:
        query = query.filter(EntityAuditLog.organization_id == organization_id)
    if table_name:
        query = query.filter(EntityAuditLog.table_name == table_name)
    if record_id:
        query = query.filter(EntityAuditLog.record_id == record_id)
    if user_id:
        query = query.filter(EntityAuditLog.user_id == user_id)
    if action:
        query = query.filter(EntityAuditLog.action == action)
    if date_from:
        query = query.filter(EntityAuditLog.created_at >= date_from)
    if date_to:
        query = query.filter(EntityAuditLog.created_at <= date_to)

    total = query.count()
    total_pages = max(1, math.ceil(total / page_size))

    logs = (
        query.order_by(desc(EntityAuditLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Batch-resolve user names and org names
    uid_set = {log.user_id for log in logs if log.user_id}
    oid_set = {log.organization_id for log in logs if log.organization_id}

    # For logs with NULL user_id, use record_id as fallback when table is 'users'
    # (e.g., login events where the user IS the record being modified)
    record_user_ids = set()
    for log in logs:
        if not log.user_id and log.table_name == "users" and log.record_id:
            uid_set.add(log.record_id)
            record_user_ids.add(log.record_id)

    # For logs with NULL organization_id, use record_id when table is 'organizations'
    record_org_ids = set()
    for log in logs:
        if not log.organization_id and log.table_name == "organizations" and log.record_id:
            oid_set.add(log.record_id)
            record_org_ids.add(log.record_id)

    user_map = _resolve_users(db, uid_set)
    org_map = _resolve_orgs(db, oid_set)

    # For user table events with no org, look up user's primary org
    user_org_map = _resolve_user_orgs(db, uid_set)
    # Add those org IDs to org_map so we can resolve names
    extra_org_ids = set(user_org_map.values()) - set(org_map.keys())
    if extra_org_ids:
        extra_orgs = _resolve_orgs(db, extra_org_ids)
        org_map.update(extra_orgs)

    items = []
    for log in logs:
        # Resolve user: prefer user_id, fall back to record_id for user table events
        effective_uid = log.user_id
        if not effective_uid and log.table_name == "users" and log.record_id:
            effective_uid = log.record_id
        u = user_map.get(effective_uid, {}) if effective_uid else {}

        # Resolve org: prefer organization_id, fall back to record_id for org table events,
        # then fall back to user's primary org
        effective_oid = log.organization_id
        if not effective_oid and log.table_name == "organizations" and log.record_id:
            effective_oid = log.record_id
        if not effective_oid and effective_uid:
            effective_oid = user_org_map.get(effective_uid)
        org_name = org_map.get(effective_oid) if effective_oid else None

        items.append(AuditLogItem(
            id=log.id,
            user_id=log.user_id or effective_uid,
            organization_id=log.organization_id or effective_oid,
            action=log.action,
            table_name=log.table_name,
            record_id=log.record_id,
            old_values=log.old_values,
            new_values=log.new_values,
            changed_fields=log.changed_fields,
            ip_address=log.ip_address,
            created_at=log.created_at,
            user_email=u.get("name") or u.get("email"),
            user_name=u.get("name"),
            user_email_address=u.get("email"),
            organization_name=org_name,
        ))

    return AuditLogListResponse(
        audit_logs=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )
