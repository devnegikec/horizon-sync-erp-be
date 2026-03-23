"""Admin user activity log endpoints.

GET    /admin/activity-logs                          — paginated list with filters
GET    /admin/activity-logs/users/{user_id}/login-history — login/login_failed entries for user
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_admin
from app.schemas.admin_activity_log import (
    ActivityLogListResponse,
    LoginHistoryResponse,
)
from app.services.user_activity_log_service import UserActivityLogService

router = APIRouter()


@router.get("", response_model=ActivityLogListResponse)
async def list_activity_logs(
    user_id: UUID | None = Query(None, description="Filter by user"),
    organization_id: UUID | None = Query(None, description="Filter by organization"),
    action: str | None = Query(None, description="Filter by action type"),
    date_from: datetime | None = Query(None, description="Filter from date"),
    date_to: datetime | None = Query(None, description="Filter to date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> ActivityLogListResponse:
    """Return a paginated list of user activity logs with optional filters."""
    service = UserActivityLogService(db)
    return service.list_activity_logs(
        user_id=user_id,
        organization_id=organization_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}/login-history", response_model=LoginHistoryResponse)
async def get_login_history(
    user_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> LoginHistoryResponse:
    """Return login and login_failed entries for a specific user."""
    service = UserActivityLogService(db)
    return service.get_login_history(
        user_id=user_id,
        page=page,
        page_size=page_size,
    )
