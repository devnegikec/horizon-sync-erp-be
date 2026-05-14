"""Stock entry and stock_entry_items schemas"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.stock_entry import StockEntry

from app.schemas.common import PaginationMeta


class WarehouseInfo(BaseModel):
    """Warehouse name and code from warehouses_extended table."""

    name: str
    code: str


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
    description: str | None = Field(None, max_length=1000)
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
    description: str | None = Field(None, max_length=1000)
    extra_data: dict | None = None


class StockEntryItemResponse(BaseModel):
    id: UUID
    organization_id: UUID
    stock_entry_id: UUID
    item_id: UUID
    item_name: str | None = None
    item_code: str | None = None
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
    stock_entry_no: str | None = Field(None, min_length=1, max_length=100)
    stock_entry_type: str  # material_receipt, material_issue, material_transfer, etc.
    from_warehouse_id: UUID | None = None
    to_warehouse_id: UUID | None = None
    posting_date: datetime
    posting_time: str | None = Field(None, max_length=10)
    status: str = Field(default="draft")  # draft, submitted, cancelled
    reference_type: str | None = Field(None, max_length=50)
    reference_id: UUID | None = None
    remarks: str | None = Field(None, max_length=1000)
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
    remarks: str | None = Field(None, max_length=1000)
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
    from_warehouse: WarehouseInfo | None = None
    to_warehouse: WarehouseInfo | None = None
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
    from_warehouse: WarehouseInfo | None = None
    to_warehouse: WarehouseInfo | None = None

    model_config = ConfigDict(from_attributes=True)


class StockEntryListResponse(BaseModel):
    stock_entries: list[StockEntryListItem]
    pagination: PaginationMeta


def stock_entry_to_list_item(e: StockEntry) -> StockEntryListItem:
    """Build list item from ORM without embedding warehouses (avoids lazy-load loops)."""

    from_warehouse = None
    if getattr(e, "from_warehouse", None) is not None:
        from_warehouse = WarehouseInfo(
            name=e.from_warehouse.name, code=e.from_warehouse.code
        )
    to_warehouse = None
    if getattr(e, "to_warehouse", None) is not None:
        to_warehouse = WarehouseInfo(name=e.to_warehouse.name, code=e.to_warehouse.code)
    return StockEntryListItem(
        id=e.id,
        stock_entry_no=e.stock_entry_no,
        stock_entry_type=e.stock_entry_type.value
        if hasattr(e.stock_entry_type, "value")
        else str(e.stock_entry_type),
        from_warehouse_id=e.from_warehouse_id,
        to_warehouse_id=e.to_warehouse_id,
        posting_date=e.posting_date,
        status=e.status.value
        if hasattr(e.status, "value")
        else str(e.status)
        if e.status
        else None,
        created_at=e.created_at,
        from_warehouse=from_warehouse,
        to_warehouse=to_warehouse,
    )


def stock_entry_to_response(e: StockEntry) -> StockEntryResponse:
    """Build response from ORM without embedding warehouses (avoids lazy-load loops)."""

    from_warehouse = None
    if getattr(e, "from_warehouse", None) is not None:
        from_warehouse = WarehouseInfo(
            name=e.from_warehouse.name, code=e.from_warehouse.code
        )
    to_warehouse = None
    if getattr(e, "to_warehouse", None) is not None:
        to_warehouse = WarehouseInfo(name=e.to_warehouse.name, code=e.to_warehouse.code)

    items = []
    if hasattr(e, "items") and e.items:
        for item in e.items:
            item_resp = StockEntryItemResponse.model_validate(item)
            # Populate item_name and item_code from the related Item model
            if hasattr(item, "item") and item.item:
                item_resp.item_name = item.item.item_name
                item_resp.item_code = item.item.item_code
            items.append(item_resp)

    return StockEntryResponse(
        id=e.id,
        organization_id=e.organization_id,
        stock_entry_no=e.stock_entry_no,
        stock_entry_type=e.stock_entry_type.value
        if hasattr(e.stock_entry_type, "value")
        else str(e.stock_entry_type),
        from_warehouse_id=e.from_warehouse_id,
        to_warehouse_id=e.to_warehouse_id,
        posting_date=e.posting_date,
        posting_time=e.posting_time,
        status=e.status.value
        if hasattr(e.status, "value")
        else str(e.status)
        if e.status
        else None,
        reference_type=e.reference_type,
        reference_id=e.reference_id,
        remarks=e.remarks,
        total_value=e.total_value,
        expense_account_id=e.expense_account_id,
        cost_center_id=e.cost_center_id,
        is_backflush=e.is_backflush,
        bom_id=e.bom_id,
        extra_data=e.extra_data,
        submitted_at=e.submitted_at,
        cancelled_at=e.cancelled_at,
        created_at=e.created_at,
        updated_at=e.updated_at,
        created_by=e.created_by,
        updated_by=e.updated_by,
        from_warehouse=from_warehouse,
        to_warehouse=to_warehouse,
        items=items,
    )
