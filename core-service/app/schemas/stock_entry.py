"""Stock entry and stock_entry_items schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta

# ----- StockEntryItem -----


class StockEntryItemBase(BaseModel):
    item_id: UUID
    source_warehouse_id: UUID | None = None
    target_warehouse_id: UUID | None = None
    qty: Decimal | float = Field(..., gt=0)
    uom: str = Field(..., min_length=1, max_length=50)
    basic_rate: Decimal | float | None = None
    valuation_rate: Decimal | float | None = None
    batch_no: str | None = Field(None, max_length=100)
    serial_nos: list[str] | None = None
    description: str | None = None
    extra_data: dict | None = None


class StockEntryItemCreate(StockEntryItemBase):
    pass


class StockEntryItemUpdate(BaseModel):
    source_warehouse_id: UUID | None = None
    target_warehouse_id: UUID | None = None
    qty: Decimal | float | None = Field(None, gt=0)
    uom: str | None = Field(None, min_length=1, max_length=50)
    basic_rate: Decimal | float | None = None
    valuation_rate: Decimal | float | None = None
    batch_no: str | None = Field(None, max_length=100)
    serial_nos: list[str] | None = None
    description: str | None = None
    extra_data: dict | None = None


class StockEntryItemResponse(BaseModel):
    id: UUID
    organization_id: UUID
    stock_entry_id: UUID
    item_id: UUID
    source_warehouse_id: UUID | None = None
    target_warehouse_id: UUID | None = None
    qty: Decimal
    uom: str
    basic_rate: Decimal | None = None
    basic_amount: Decimal | None = None
    valuation_rate: Decimal | None = None
    batch_no: str | None = None
    serial_nos: list | None = None
    description: str | None = None
    extra_data: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ----- StockEntry -----


class StockEntryBase(BaseModel):
    stock_entry_no: str = Field(..., min_length=1, max_length=100)
    stock_entry_type: str  # material_receipt, material_issue, material_transfer, etc.
    from_warehouse_id: UUID | None = None
    to_warehouse_id: UUID | None = None
    posting_date: datetime
    posting_time: str | None = Field(None, max_length=10)
    status: str = Field(default="draft")  # draft, submitted, cancelled
    reference_type: str | None = Field(None, max_length=50)
    reference_id: UUID | None = None
    remarks: str | None = None
    total_value: Decimal | float | None = None
    expense_account_id: UUID | None = None
    cost_center_id: UUID | None = None
    is_backflush: bool | None = None
    bom_id: UUID | None = None
    extra_data: dict | None = None


class StockEntryCreate(StockEntryBase):
    items: list[StockEntryItemCreate] = Field(default_factory=list)


class StockEntryUpdate(BaseModel):
    from_warehouse_id: UUID | None = None
    to_warehouse_id: UUID | None = None
    posting_date: datetime | None = None
    posting_time: str | None = Field(None, max_length=10)
    status: str | None = None
    reference_type: str | None = Field(None, max_length=50)
    reference_id: UUID | None = None
    remarks: str | None = None
    total_value: Decimal | float | None = None
    expense_account_id: UUID | None = None
    cost_center_id: UUID | None = None
    is_backflush: bool | None = None
    bom_id: UUID | None = None
    extra_data: dict | None = None


class StockEntryResponse(BaseModel):
    id: UUID
    organization_id: UUID
    stock_entry_no: str
    stock_entry_type: str
    from_warehouse_id: UUID | None = None
    to_warehouse_id: UUID | None = None
    posting_date: datetime
    posting_time: str | None = None
    status: str | None = None
    reference_type: str | None = None
    reference_id: UUID | None = None
    remarks: str | None = None
    total_value: Decimal | None = None
    expense_account_id: UUID | None = None
    cost_center_id: UUID | None = None
    is_backflush: bool | None = None
    bom_id: UUID | None = None
    extra_data: dict | None = None
    submitted_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    items: list[StockEntryItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class StockEntryListItem(BaseModel):
    id: UUID
    stock_entry_no: str
    stock_entry_type: str
    from_warehouse_id: UUID | None = None
    to_warehouse_id: UUID | None = None
    posting_date: datetime
    status: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockEntryListResponse(BaseModel):
    stock_entries: list[StockEntryListItem]
    pagination: PaginationMeta
