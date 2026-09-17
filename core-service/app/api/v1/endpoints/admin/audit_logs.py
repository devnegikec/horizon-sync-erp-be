"""Admin audit log endpoints — cross-org access for system admins.

GET /admin/audit-logs          — paginated list with optional filters
GET /admin/audit-logs/{record_id}/history — record change history
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.authorization import SYSTEM_ADMIN_REPORTING_READ
from app.dependencies import CurrentUser, require_permission
from app.schemas.audit_log import AuditLogHistoryResponse, AuditLogListResponse
from app.services.audit_log_service import AuditLogService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    organization_id: UUID | None = Query(None, description="Filter by organization"),
    table_name: str | None = Query(None, description="Filter by table name"),
    record_id: UUID | None = Query(None, description="Filter by record ID"),
    user_id: UUID | None = Query(None, description="Filter by user ID"),
    action: str | None = Query(
        None, description="Filter by action (CREATE, UPDATE, DELETE)"
    ),
    date_from: datetime | None = Query(None, description="Filter from date"),
    date_to: datetime | None = Query(None, description="Filter to date"),
    changed_field: str | None = Query(None, description="Filter by changed field name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_REPORTING_READ)),
) -> AuditLogListResponse:
    """Return a cross-org paginated list of audit log entries."""
    service = AuditLogService(db)
    return service.list_audit_logs(
        organization_id=organization_id,
        table_name=table_name,
        record_id=record_id,
        user_id=user_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
        changed_field=changed_field,
        page=page,
        page_size=page_size,
    )


@router.get("/{record_id}/history", response_model=AuditLogHistoryResponse)
async def get_record_history(
    record_id: UUID,
    table_name: str = Query(..., description="Table name for the record"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_REPORTING_READ)),
) -> AuditLogHistoryResponse:
    """Return the change history for a specific record (cross-org)."""
    service = AuditLogService(db)
    return service.get_record_history(
        table_name=table_name,
        record_id=record_id,
        page=page,
        page_size=page_size,
    )
