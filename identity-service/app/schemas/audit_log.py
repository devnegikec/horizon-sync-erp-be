"""Audit log related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SystemAdminAuditLogBase(BaseModel):
    """Base audit log schema with common fields"""

    action_type: str = Field(..., description="Type of action performed")
    admin_user_id: UUID = Field(..., description="ID of admin user who performed action")
    admin_username: str = Field(..., description="Username of admin user")
    target_user_id: UUID | None = Field(None, description="ID of target user (if applicable)")
    target_username: str | None = Field(None, description="Username of target user")
    target_organization_id: UUID | None = Field(None, description="ID of target organization (if applicable)")
    target_organization_name: str | None = Field(None, description="Name of target organization")
    changes_made: dict = Field(default_factory=dict, description="Details of changes made")
    performed_by: str = Field(..., description="Full name of admin user who performed action")
    notes: str | None = Field(None, max_length=1000, description="Optional notes about the action")


class SystemAdminAuditLogCreate(SystemAdminAuditLogBase):
    """Schema for creating a new audit log entry"""

    action_id: str = Field(..., max_length=255, description="Unique identifier for the action")


class SystemAdminAuditLogResponse(SystemAdminAuditLogBase):
    """Schema for audit log response"""

    action_id: str
    performed_date: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListItem(SystemAdminAuditLogResponse):
    """Schema for audit log in list response (same as response for now)"""
    
    pass


class AuditLogPaginationMeta(BaseModel):
    """Pagination metadata for audit logs"""

    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class SystemAdminAuditLogListResponse(BaseModel):
    """Schema for paginated audit log list response"""

    data: list[AuditLogListItem]
    pagination: AuditLogPaginationMeta


class AuditLogFilters(BaseModel):
    """Schema for audit log filtering parameters"""
    
    admin_user_id: UUID | None = Field(None, description="Filter by admin user ID")
    target_organization_id: UUID | None = Field(None, description="Filter by target organization ID")
    action_type: str | None = Field(None, description="Filter by action type")
    start_date: datetime | None = Field(None, description="Filter by start date")
    end_date: datetime | None = Field(None, description="Filter by end date")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=500, description="Items per page")


class ActionTypeInfo(BaseModel):
    """Schema for action type information"""
    
    value: str
    label: str
    description: str


class AuditLogStatsResponse(BaseModel):
    """Schema for audit log statistics"""
    
    total_actions: int
    actions_by_type: dict[str, int]
    actions_by_admin: dict[str, int]
    recent_actions_count: int  # Actions in last 24 hours
    available_action_types: list[ActionTypeInfo]