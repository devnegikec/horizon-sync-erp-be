"""Pydantic schemas for admin dashboard responses."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class OrgMetrics(BaseModel):
    """Organization metrics for the admin dashboard."""

    total: int = Field(description="Total number of organizations")
    active: int = Field(description="Number of active organizations")
    on_trial: int = Field(description="Number of organizations on trial")


class UserMetrics(BaseModel):
    """User metrics for the admin dashboard."""

    total: int = Field(description="Total number of users")
    active: int = Field(description="Number of active users")


class RevenueMetrics(BaseModel):
    """Revenue metrics for the admin dashboard."""

    total_invoiced: Decimal = Field(
        default=Decimal("0"), description="Sum of grand_total for paid invoices"
    )
    total_outstanding: Decimal = Field(
        default=Decimal("0"),
        description="Sum of outstanding_amount for pending/partial/overdue invoices",
    )
    total_received: Decimal = Field(
        default=Decimal("0"), description="Sum of amount for completed payments"
    )


class ActivityLogItem(BaseModel):
    """Single activity log entry for the dashboard."""

    id: UUID
    user_id: UUID
    organization_id: UUID | None = None
    action: str
    resource_type: str | None = None
    resource_id: UUID | None = None
    ip_address: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class DashboardOverview(BaseModel):
    """Combined dashboard overview response."""

    organizations: OrgMetrics
    users: UserMetrics
    revenue: RevenueMetrics
    recent_activity: list[ActivityLogItem]
