"""Stock reconciliation and items schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta

# ----- StockReconciliationItem -----


class StockReconciliationItemBase(BaseModel):
    item_id: UUID
    warehouse_id: UUID
    current_qty: Decimal | float | None = None
    qty: Decimal | float = Field(..., gt=0)
    qty_difference: Decimal | float | None = None
    current_valuation_rate: Decimal | float | None = None
    valuation_rate: Decimal | float | None = None
    batch_no: str | None = Field(None, max_length=100)
    serial_nos: list | None = None
    extra_data: dict | None = None


class StockReconciliationItemCreate(StockReconciliationItemBase):
    pass


class StockReconciliationItemUpdate(BaseModel):
    current_qty: Decimal | float | None = None
    qty: Decimal | float | None = Field(None, gt=0)
    qty_difference: Decimal | float | None = None
    current_valuation_rate: Decimal | float | None = None
    valuation_rate: Decimal | float | None = None
    batch_no: str | None = Field(None, max_length=100)
    serial_nos: list | None = None
    extra_data: dict | None = None


class StockReconciliationItemResponse(BaseModel):
    id: UUID
    organization_id: UUID
    reconciliation_id: UUID
    item_id: UUID
    warehouse_id: UUID
    current_qty: Decimal | None = None
    qty: Decimal
    qty_difference: Decimal | None = None
    current_valuation_rate: Decimal | None = None
    valuation_rate: Decimal | None = None
    batch_no: str | None = None
    serial_nos: list | None = None
    extra_data: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ----- StockReconciliation -----


class StockReconciliationBase(BaseModel):
    reconciliation_no: str = Field(..., min_length=1, max_length=100)
    purpose: str | None = Field(None, max_length=100)
    posting_date: datetime
    posting_time: str | None = Field(None, max_length=10)
    status: str = Field(default="draft")
    expense_account_id: UUID | None = None
    difference_account_id: UUID | None = None
    remarks: str | None = None
    extra_data: dict | None = None


class StockReconciliationCreate(StockReconciliationBase):
    items: list[StockReconciliationItemCreate] = Field(default_factory=list)


class StockReconciliationUpdate(BaseModel):
    purpose: str | None = Field(None, max_length=100)
    posting_date: datetime | None = None
    posting_time: str | None = Field(None, max_length=10)
    status: str | None = None
    expense_account_id: UUID | None = None
    difference_account_id: UUID | None = None
    remarks: str | None = None
    extra_data: dict | None = None


class StockReconciliationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    reconciliation_no: str
    purpose: str | None = None
    posting_date: datetime
    posting_time: str | None = None
    status: str | None = None
    expense_account_id: UUID | None = None
    difference_account_id: UUID | None = None
    remarks: str | None = None
    extra_data: dict | None = None
    submitted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    items: list[StockReconciliationItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class StockReconciliationListItem(BaseModel):
    id: UUID
    reconciliation_no: str
    purpose: str | None = None
    posting_date: datetime
    status: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockReconciliationListResponse(BaseModel):
    stock_reconciliations: list[StockReconciliationListItem]
    pagination: PaginationMeta
