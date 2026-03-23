"""Admin dashboard endpoint — GET /admin/dashboard/overview."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_admin
from app.schemas.admin_dashboard import DashboardOverview
from app.services.admin_dashboard_service import AdminDashboardService

router = APIRouter()


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    date_from: datetime | None = Query(None, description="Start of date range filter"),
    date_to: datetime | None = Query(None, description="End of date range filter"),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> DashboardOverview:
    """
    Return aggregated dashboard metrics for the admin portal.

    Includes organization counts, user counts, revenue summary,
    and the 10 most recent activity log entries.
    Optional date_from / date_to filters apply to revenue and activity metrics.
    """
    service = AdminDashboardService(db)
    return service.get_overview(date_from=date_from, date_to=date_to)
