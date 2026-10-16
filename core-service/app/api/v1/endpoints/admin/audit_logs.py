"""Admin audit log endpoints — cross-org access for system admins.

GET /admin/audit-logs          — paginated list with optional filters
GET /admin/audit-logs/{record_id}/history — record change history
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.authorization import SYSTEM_ADMIN_REPORTING_READ
from app.core.audit_modules import MODULES, tables_for_module
from app.dependencies import CurrentUser, require_permission
from app.schemas.audit_log import (
    AuditLogHistoryResponse,
    AuditLogListResponse,
    AuditModuleInfo,
    AuditModuleListResponse,
)
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
    role: str | None = Query(
        None, description="Filter by user role (JWT user_type value)"
    ),
    module: str | None = Query(
        None,
        description=(
            "Filter by business module (Inventory, WMS, Revenue, QSeal, "
            "Users, Roles, Settings, Other)"
        ),
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
    table_names: list[str] | None = None
    if module:
        if module not in MODULES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown module '{module}'. Valid modules: {', '.join(MODULES)}",
            )
        table_names = tables_for_module(module)

    service = AuditLogService(db)
    return service.list_audit_logs(
        organization_id=organization_id,
        table_name=table_name,
        record_id=record_id,
        user_id=user_id,
        action=action,
        role=role,
        table_names=table_names,
        date_from=date_from,
        date_to=date_to,
        changed_field=changed_field,
        page=page,
        page_size=page_size,
    )


@router.get("/modules", response_model=AuditModuleListResponse)
async def list_audit_modules(
    current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_REPORTING_READ)),
) -> AuditModuleListResponse:
    """Return the module → tables catalog for the audit UI filter."""
    return AuditModuleListResponse(
        modules=[
            AuditModuleInfo(module=m, tables=tables_for_module(m))
            for m in MODULES
        ]
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
