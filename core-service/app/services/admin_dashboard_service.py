"""Service layer for the admin dashboard.

Orchestrates repository calls and assembles the DashboardOverview response.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories.admin_dashboard_repository import AdminDashboardRepository
from app.schemas.admin_dashboard import (
    ActivityLogItem,
    DashboardOverview,
    OrgMetrics,
    RevenueMetrics,
    UserMetrics,
)


class AdminDashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdminDashboardRepository(db)

    def get_overview(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> DashboardOverview:
        """Assemble the full dashboard overview from individual metric queries."""
        org_data = self.repo.get_org_metrics()
        user_data = self.repo.get_user_metrics()
        revenue_data = self.repo.get_revenue_metrics(
            date_from=date_from, date_to=date_to
        )
        activity_rows = self.repo.get_recent_activity(
            limit=10, date_from=date_from, date_to=date_to
        )

        return DashboardOverview(
            organizations=OrgMetrics(**org_data),
            users=UserMetrics(**user_data),
            revenue=RevenueMetrics(**revenue_data),
            recent_activity=[
                ActivityLogItem.model_validate(row) for row in activity_rows
            ],
        )
