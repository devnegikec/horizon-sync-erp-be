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
    user_agent: str | None = None
    created_at: datetime | None = None

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
    """Return paginated entity audit logs for identity-service models."""
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

    return AuditLogListResponse(
        audit_logs=[AuditLogItem.model_validate(log) for log in logs],
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )
