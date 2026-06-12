"""WMS Worker schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class WMSWorkerBase(BaseModel):
    warehouse_id: UUID
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    login_username: str | None = Field(None, max_length=100)
    employee_id: str | None = Field(None, max_length=100, description="Unique employee identifier assigned at creation")
    role: str = Field(default="warehouse_worker", pattern="^(warehouse_worker|receiver|picker|operator|supervisor|manager)$")
    status: str = Field(default="active", pattern="^(active|inactive|disabled)$")
    is_active: bool = True


class WMSWorkerCreate(WMSWorkerBase):
    password: str | None = Field(None, min_length=6, max_length=100)
    barcode: str | None = Field(None, max_length=100)
    extra_data: dict | None = None


class WMSWorkerUpdate(BaseModel):
    warehouse_id: UUID | None = None
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    login_username: str | None = Field(None, max_length=100)
    employee_id: str | None = Field(None, max_length=100)
    password: str | None = Field(None, min_length=6, max_length=100)
    barcode: str | None = Field(None, max_length=100)
    role: str | None = Field(None, pattern="^(warehouse_worker|receiver|picker|operator|supervisor|manager)$")
    status: str | None = Field(None, pattern="^(active|inactive|disabled)$")
    is_active: bool | None = None
    extra_data: dict | None = None


class WMSWorkerResponse(WMSWorkerBase):
    id: UUID
    organization_id: UUID
    barcode: str | None = None
    employee_id: str | None = None
    last_login_at: datetime | None = None
    extra_data: dict | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class WMSWorkerListResponse(BaseModel):
    workers: list[WMSWorkerResponse]
    pagination: PaginationMeta


class BarcodeLoginRequest(BaseModel):
    barcode: str = Field(..., min_length=1, max_length=100)


class BarcodeLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    worker: WMSWorkerResponse
