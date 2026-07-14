"""WMS Device schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class WMSDeviceBase(BaseModel):
    warehouse_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    device_code: str = Field(..., min_length=1, max_length=100)
    device_type: str | None = Field(None, max_length=100)
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    os_version: str | None = None
    assigned_to_worker_id: UUID | None = None
    status: str = Field(default="active", pattern="^(active|inactive|maintenance)$")


class WMSDeviceCreate(WMSDeviceBase):
    extra_data: dict | None = None


class WMSDeviceUpdate(BaseModel):
    warehouse_id: UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    device_code: str | None = Field(None, min_length=1, max_length=100)
    device_type: str | None = Field(None, max_length=100)
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    os_version: str | None = None
    assigned_to_worker_id: UUID | None = None
    status: str | None = Field(None, pattern="^(active|inactive|maintenance)$")
    extra_data: dict | None = None


class WMSDeviceResponse(WMSDeviceBase):
    id: UUID
    organization_id: UUID
    last_synced_at: datetime | None = None
    extra_data: dict | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class WMSDeviceListResponse(BaseModel):
    devices: list[WMSDeviceResponse]
    pagination: PaginationMeta
