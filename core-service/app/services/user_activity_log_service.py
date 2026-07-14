"""Service layer for user activity log operations.

Orchestrates repository calls, extracts IP/user-agent from requests,
and assembles paginated responses.

Note: Login/logout events originate from identity-service.
Core-service logs data CRUD events. Identity-service should call
core-service's activity log endpoint (or write directly to shared DB)
for login events.
"""

import math
from datetime import datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.repositories.user_activity_log_repository import UserActivityLogRepository
from app.schemas.admin_activity_log import (
    ActivityLogCreate,
    ActivityLogItem,
    ActivityLogListResponse,
    LoginHistoryResponse,
)
from app.schemas.common import PaginationMeta


class UserActivityLogService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserActivityLogRepository(db)

    # ── Log an activity ──────────────────────────────────────────────

    def log_activity(
        self,
        data: ActivityLogCreate,
        request: Request | None = None,
    ) -> ActivityLogItem:
        """Create an activity log entry, optionally extracting IP and user-agent from the request."""
        log_data = data.model_dump()

        # Extract IP and user-agent from request if not explicitly provided
        if request:
            if not log_data.get("ip_address"):
                log_data["ip_address"] = (
                    request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                    or request.client.host
                    if request.client
                    else None
                )
            if not log_data.get("user_agent"):
                log_data["user_agent"] = request.headers.get("user-agent")

        created = self.repo.create(log_data)
        self.db.commit()
        return ActivityLogItem(**created)

    # ── List activity logs ───────────────────────────────────────────

    def list_activity_logs(
        self,
        user_id: UUID | None = None,
        organization_id: UUID | None = None,
        action: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ActivityLogListResponse:
        """Return paginated activity logs with optional filters."""
        logs, total = self.repo.list_activity_logs(
            user_id=user_id,
            organization_id=organization_id,
            action=action,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
        total_pages = max(1, math.ceil(total / page_size))
        return ActivityLogListResponse(
            activity_logs=[ActivityLogItem(**log) for log in logs],
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )

    # ── Login history ────────────────────────────────────────────────

    def get_login_history(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> LoginHistoryResponse:
        """Return login/login_failed entries for a specific user."""
        logs, total = self.repo.get_login_history(
            user_id=user_id,
            page=page,
            page_size=page_size,
        )
        total_pages = max(1, math.ceil(total / page_size))
        return LoginHistoryResponse(
            user_id=user_id,
            login_history=[ActivityLogItem(**log) for log in logs],
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )
