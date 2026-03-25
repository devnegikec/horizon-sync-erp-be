"""Pydantic schemas for admin user activity log operations.

Covers activity log creation, list responses, and login history.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


# ── Create ───────────────────────────────────────────────────────────


class ActivityLogCreate(BaseModel):
    """Schema for creating a new activity log entry."""

    user_id: UUID
    organization_id: UUID
    action: str = Field(
        ...,
        pattern=r"^(login|logout|login_failed|page_view|data_create|data_update|data_delete)$",
    )
    resource_type: str | None = None
    resource_id: UUID | None = None
    ip_address: str | None = Field(None, max_length=45)
    user_agent: str | None = None
    metadata: dict[str, Any] | None = None


# ── List / Detail ────────────────────────────────────────────────────


class ActivityLogItem(BaseModel):
    """Single activity log entry in a paginated list."""

    id: UUID
    user_id: UUID
    organization_id: UUID
    action: str
    resource_type: str | None = None
    resource_id: UUID | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime

    # Joined fields
    user_email: str | None = None
    organization_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ActivityLogListResponse(BaseModel):
    """Paginated list of activity log entries."""

    activity_logs: list[ActivityLogItem]
    pagination: PaginationMeta


# ── Login History ────────────────────────────────────────────────────


class LoginHistoryResponse(BaseModel):
    """Login history for a specific user (login + login_failed events)."""

    user_id: UUID
    login_history: list[ActivityLogItem]
    pagination: PaginationMeta
