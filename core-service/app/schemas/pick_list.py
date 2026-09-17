"""Pick list schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class NestedReference(BaseModel):
    """Nested reference details (id, name, code)"""

    id: str
    name: str
    code: str


class NestedReferenceWithType(BaseModel):
    """Nested reference with type (for sales_order, etc.)"""

    id: str
    reference_type: str
    name: str
    code: str


class PickListItemBase(BaseModel):
    item_id: UUID
    warehouse_id: UUID
    qty: Decimal | float = Field(..., gt=0)
    uom: str = Field(..., min_length=1, max_length=50)
    per_case_qty: Decimal | float | None = None
    case_qty: Decimal | float | None = None
    loose_qty: Decimal | float | None = None
    batch_no: str | None = Field(None, max_length=100)
    serial_nos: list[str] | None = None
    sort_order: int = 0


class PickListItemCreate(PickListItemBase):
    pass


class PickListItemResponse(BaseModel):
    id: UUID
    organization_id: UUID
    item: NestedReference | None = None
    warehouse: NestedReference | None = None
    qty: Decimal
    picked_qty: Decimal
    uom: str
    per_case_qty: Decimal | None = None
    case_qty: Decimal | None = None
    loose_qty: Decimal | None = None
    batch_no: str | None
    sort_order: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PickListBase(BaseModel):
    pick_list_no: str | None = Field(None, min_length=1, max_length=100)
    warehouse_id: UUID
    status: str = Field(
        default="draft", pattern="^(draft|in_progress|completed|cancelled)$"
    )
    pick_date: datetime | None = None
    reference_type: str | None = Field(None, max_length=50)
    reference_id: UUID | None = None
    remarks: str | None = Field(None, max_length=1000)


class PickListCreate(PickListBase):
    items: list[PickListItemCreate] = Field(default_factory=list)


class PickListUpdate(BaseModel):
    warehouse_id: UUID | None = None
    status: str | None = Field(
        None, pattern="^(draft|in_progress|completed|cancelled)$"
    )
    pick_date: datetime | None = None
    remarks: str | None = Field(None, max_length=1000)
    assigned_to: UUID | None = None


class PickListResponse(PickListBase):
    id: UUID
    organization_id: UUID
    warehouse: NestedReference | None = None
    reference: NestedReferenceWithType | None = None
    assigned_to: UUID | None = None
    completed_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    items: list[PickListItemResponse] = []
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
    reference_type: str | None = None
    reference_id: UUID | None = None
    sales_order_no: str | None = None
    items_count: int = 0
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PickListListResponse(BaseModel):
    pick_lists: list[PickListListItem]
    pagination: PaginationMeta
