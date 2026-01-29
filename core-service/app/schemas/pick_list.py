"""Pick list schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class PickListItemBase(BaseModel):
    item_id: UUID
    warehouse_id: UUID
    qty: Decimal | float = Field(..., gt=0)
    uom: str = Field(..., min_length=1, max_length=50)
    batch_no: str | None = Field(None, max_length=100)
    serial_nos: list[str] | None = None
    sort_order: int = 0


class PickListItemCreate(PickListItemBase):
    pass


class PickListItemResponse(BaseModel):
    id: UUID
    organization_id: UUID
    pick_list_id: UUID
    item_id: UUID
    warehouse_id: UUID
    qty: Decimal
    picked_qty: Decimal
    uom: str
    batch_no: str | None
    sort_order: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PickListBase(BaseModel):
    pick_list_no: str = Field(..., min_length=1, max_length=100)
    warehouse_id: UUID
    status: str = Field(
        default="draft", pattern="^(draft|in_progress|completed|cancelled)$"
    )
    pick_date: datetime | None = None
    reference_type: str | None = Field(None, max_length=50)
    reference_id: UUID | None = None
    remarks: str | None = None


class PickListCreate(PickListBase):
    items: list[PickListItemCreate] = Field(default_factory=list)


class PickListUpdate(BaseModel):
    warehouse_id: UUID | None = None
    status: str | None = Field(
        None, pattern="^(draft|in_progress|completed|cancelled)$"
    )
    pick_date: datetime | None = None
    remarks: str | None = None


class PickListResponse(PickListBase):
    id: UUID
    organization_id: UUID
    completed_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PickListItemListItem(BaseModel):
    id: UUID
    pick_list_id: UUID
    item_id: UUID
    warehouse_id: UUID
    qty: Decimal
    picked_qty: Decimal
    uom: str
    model_config = ConfigDict(from_attributes=True)


class PickListListItem(BaseModel):
    id: UUID
    organization_id: UUID
    pick_list_no: str
    warehouse_id: UUID
    status: str
    pick_date: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PickListListResponse(BaseModel):
    pick_lists: list[PickListListItem]
    pagination: PaginationMeta
