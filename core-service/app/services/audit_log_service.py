"""Service layer for audit log operations.

Delegates to AuditLogRepository and assembles paginated responses.
"""

import math
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.audit_log import (
    AuditLogDetail,
    AuditLogHistoryResponse,
    AuditLogListItem,
    AuditLogListResponse,
)
from app.schemas.common import PaginationMeta


class AuditLogService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AuditLogRepository(db)

    def list_audit_logs(
        self,
        organization_id: UUID | None = None,
        table_name: str | None = None,
        record_id: UUID | None = None,
        user_id: UUID | None = None,
        action: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        changed_field: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AuditLogListResponse:
        logs, total = self.repo.list_audit_logs(
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
        total_pages = max(1, math.ceil(total / page_size))
        return AuditLogListResponse(
            audit_logs=[AuditLogListItem(**log) for log in logs],
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )

    def get_record_history(
        self,
        table_name: str,
        record_id: UUID,
        organization_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AuditLogHistoryResponse:
        logs, total = self.repo.get_record_history(
            table_name=table_name,
            record_id=record_id,
            organization_id=organization_id,
            page=page,
            page_size=page_size,
        )
        total_pages = max(1, math.ceil(total / page_size))
        return AuditLogHistoryResponse(
            record_id=record_id,
            table_name=table_name,
            history=[AuditLogDetail(**log) for log in logs],
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )
