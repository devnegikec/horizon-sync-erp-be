"""Pydantic schemas for QR Product Settings"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

SettingType = Literal["serial_prefix", "channel", "destination", "shelf_life"]


class QRProductSettingCreate(BaseModel):
    setting_type: SettingType
    value: str = Field(..., max_length=100)
    label: str = Field(..., max_length=150)
    description: str | None = None
    sort_order: int = 0
    is_active: bool = True
    extra_data: dict[str, Any] | None = None


class QRProductSettingUpdate(BaseModel):
    value: str | None = Field(None, max_length=100)
    label: str | None = Field(None, max_length=150)
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    extra_data: dict[str, Any] | None = None


class QRProductSettingResponse(BaseModel):
    id: UUID
    organization_id: UUID
    setting_type: str
    value: str
    label: str
    description: str | None
    sort_order: int
    is_active: bool
    extra_data: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QRProductSettingListResponse(BaseModel):
    settings: list[QRProductSettingResponse]
    pagination: dict[str, Any]
