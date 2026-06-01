"""Warehouse-user assignment schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class WarehouseUserBase(BaseModel):
    user_id: UUID
    warehouse_id: UUID
    role: str = Field(default="operator", pattern="^(supervisor|manager|operator|coordinator)$")
    is_primary: bool = False
    is_active: bool = True


class WarehouseUserCreate(WarehouseUserBase):
    """Schema for assigning a user to a warehouse"""

    extra_data: dict | None = None


class WarehouseUserUpdate(BaseModel):
    role: str | None = Field(
        None, pattern="^(supervisor|manager|operator|coordinator)$"
    )
    is_primary: bool | None = None
    is_active: bool | None = None
    extra_data: dict | None = None


class WarehouseUserResponse(WarehouseUserBase):
    id: UUID
    organization_id: UUID
    warehouse_name: str | None = None
    warehouse_code: str | None = None
    extra_data: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseUserListResponse(BaseModel):
    users: list[WarehouseUserResponse]
    pagination: PaginationMeta
