"""Put away rule schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class PutAwayRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    item_id: UUID | None = None
    item_group_id: UUID | None = None
    warehouse_id: UUID
    capacity: int | None = None
    priority: int | None = None
    min_qty: int | None = None
    max_qty: int | None = None
    is_active: bool = True
    extra_data: dict | None = None


class PutAwayRuleCreate(PutAwayRuleBase):
    pass


class PutAwayRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    item_id: UUID | None = None
    item_group_id: UUID | None = None
    warehouse_id: UUID | None = None
    capacity: int | None = None
    priority: int | None = None
    min_qty: int | None = None
    max_qty: int | None = None
    is_active: bool | None = None
    extra_data: dict | None = None


class PutAwayRuleResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    item_id: UUID | None = None
    item_group_id: UUID | None = None
    warehouse_id: UUID
    capacity: int | None = None
    priority: int | None = None
    min_qty: int | None = None
    max_qty: int | None = None
    is_active: bool | None = None
    extra_data: dict | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class PutAwayRuleListItem(BaseModel):
    id: UUID
    name: str
    item_id: UUID | None = None
    item_group_id: UUID | None = None
    warehouse_id: UUID
    priority: int | None = None
    is_active: bool | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PutAwayRuleListResponse(BaseModel):
    put_away_rules: list[PutAwayRuleListItem]
    pagination: PaginationMeta
