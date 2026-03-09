"""Audit log schemas for API requests and responses"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AuditLogEntryResponse(BaseModel):
    """Response schema for audit log entry"""

    id: UUID
    account_id: UUID
    action: str
    user_id: str
    timestamp: datetime
    changes: dict[str, Any]
    audit_metadata: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class AuditTrailResponse(BaseModel):
    """Response schema for audit trail with pagination"""

    items: list[AuditLogEntryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class AuditTrailQueryParams(BaseModel):
    """Query parameters for audit trail filtering"""

    action: str | None = Field(
        None,
        description="Filter by action type (CREATE, UPDATE, DELETE, STATUS_CHANGE)",
    )
    start_date: datetime | None = Field(None, description="Filter by start date")
    end_date: datetime | None = Field(None, description="Filter by end date")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Items per page")
