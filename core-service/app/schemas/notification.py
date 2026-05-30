"""Notification schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class NotificationBase(BaseModel):
    type: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    entity_type: str | None = Field(None, max_length=50)
    entity_id: UUID | None = None
    entity_no: str | None = Field(None, max_length=100)
    warehouse_id: UUID | None = None
    sender_id: UUID | None = None
    sender_name: str | None = Field(None, max_length=255)


class NotificationCreate(NotificationBase):
    """Schema for creating a notification (used internally by services)"""

    organization_id: UUID
    user_id: UUID
    extra_data: dict | None = None


class NotificationUpdate(BaseModel):
    """Schema for marking a notification as read"""

    is_read: bool | None = None


class NotificationResponse(NotificationBase):
    id: UUID
    organization_id: UUID
    user_id: UUID
    is_read: bool
    read_at: datetime | None = None
    extra_data: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int
    pagination: PaginationMeta


class NotificationCountResponse(BaseModel):
    total: int
    unread: int
