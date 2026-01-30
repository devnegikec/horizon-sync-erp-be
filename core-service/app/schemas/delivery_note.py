"""Delivery note schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class DeliveryNoteItemBase(BaseModel):
    item_id: UUID
    qty: Decimal | float = Field(..., gt=0)
    uom: str = Field(..., min_length=1, max_length=50)
    rate: Decimal | float | None = None
    amount: Decimal | float | None = None
    warehouse_id: UUID | None = None
    batch_no: str | None = None
    serial_nos: list[str] | None = None
    sort_order: int = 0


class DeliveryNoteItemCreate(DeliveryNoteItemBase):
    pass


class DeliveryNoteBase(BaseModel):
    delivery_note_no: str = Field(..., min_length=1, max_length=100)
    customer_id: UUID
    delivery_date: datetime
    status: str = Field(default="draft", pattern="^(draft|submitted|cancelled)$")
    warehouse_id: UUID | None = None
    pick_list_id: UUID | None = None
    reference_type: str | None = None
    reference_id: UUID | None = None
    remarks: str | None = None


class DeliveryNoteCreate(DeliveryNoteBase):
    items: list[DeliveryNoteItemCreate] = Field(default_factory=list)


class DeliveryNoteUpdate(BaseModel):
    delivery_date: datetime | None = None
    status: str | None = Field(None, pattern="^(draft|submitted|cancelled)$")
    warehouse_id: UUID | None = None
    remarks: str | None = None


class DeliveryNoteResponse(DeliveryNoteBase):
    id: UUID
    organization_id: UUID
    submitted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DeliveryNoteListItem(BaseModel):
    id: UUID
    organization_id: UUID
    delivery_note_no: str
    customer_id: UUID
    status: str
    delivery_date: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DeliveryNoteListResponse(BaseModel):
    delivery_notes: list[DeliveryNoteListItem]
    pagination: PaginationMeta
