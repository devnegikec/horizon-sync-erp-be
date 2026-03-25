"""Service layer for the admin dashboard.

Orchestrates repository calls and identity-service API calls
to assemble the DashboardOverview response.
"""

import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.repositories.admin_dashboard_repository import AdminDashboardRepository
from app.schemas.admin_dashboard import (
    ActivityLogItem,
    DashboardOverview,
    OrgMetrics,
    RevenueMetrics,
    UserMetrics,
)

logger = logging.getLogger(__name__)

IDENTITY_API = f"{settings.identity_service_url}/api/v1/identity"


class AdminDashboardService:
    def __init__(self, db: Session, token: str | None = None):
        self.db = db
        self.repo = AdminDashboardRepository(db)
        self.token = token

    async def get_overview(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> DashboardOverview:
        """Assemble the full dashboard overview from individual metric queries."""
        org_data = await self._fetch_org_metrics()
        user_data = await self._fetch_user_metrics()
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

    # ── Identity-service API helpers ─────────────────────────────────

    def _auth_headers(self) -> dict[str, str]:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _fetch_org_metrics(self) -> dict:
        """Fetch org counts from identity-service /organizations endpoint."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Total orgs
                total_resp = await client.get(
                    f"{IDENTITY_API}/organizations",
                    params={"page": 1, "page_size": 1},
                    headers=self._auth_headers(),
                )
                total = 0
                active = 0
                on_trial = 0

                if total_resp.status_code == 200:
                    data = total_resp.json()
                    total = data.get("pagination", {}).get("total_items", 0)

                # Active orgs
                active_resp = await client.get(
                    f"{IDENTITY_API}/organizations",
                    params={"page": 1, "page_size": 1, "status": "active"},
                    headers=self._auth_headers(),
                )
                if active_resp.status_code == 200:
                    data = active_resp.json()
                    active = data.get("pagination", {}).get("total_items", 0)

                # Trial orgs
                trial_resp = await client.get(
                    f"{IDENTITY_API}/organizations",
                    params={"page": 1, "page_size": 1, "status": "trial"},
                    headers=self._auth_headers(),
                )
                if trial_resp.status_code == 200:
                    data = trial_resp.json()
                    on_trial = data.get("pagination", {}).get("total_items", 0)

                return {"total": total, "active": active, "on_trial": on_trial}
        except Exception as e:
            logger.warning(f"Failed to fetch org metrics from identity-service: {e}")
            return {"total": 0, "active": 0, "on_trial": 0}

    async def _fetch_user_metrics(self) -> dict:
        """Fetch user counts from identity-service /users endpoint."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{IDENTITY_API}/users",
                    params={"page": 1, "page_size": 1},
                    headers=self._auth_headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    total = data.get("pagination", {}).get("total_items", 0)
                    active = data.get("status_counts", {}).get("active", 0)
                    return {"total": total, "active": active}
                return {"total": 0, "active": 0}
        except Exception as e:
            logger.warning(f"Failed to fetch user metrics from identity-service: {e}")
            return {"total": 0, "active": 0}
