"""Stock settings schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StockSettingsBase(BaseModel):
    item_naming_by: str | None = Field(None, max_length=50)
    item_naming_series: str | None = Field(None, max_length=100)
    stock_entry_naming_series: str | None = Field(None, max_length=100)
    delivery_note_naming_series: str | None = Field(None, max_length=100)
    purchase_receipt_naming_series: str | None = Field(None, max_length=100)
    default_warehouse_id: UUID | None = None
    allow_negative_stock: bool | None = None
    over_delivery_receipt_allowance: Decimal | float | None = None
    over_billing_allowance: Decimal | float | None = None
    auto_indent: bool | None = None
    auto_indent_notification: dict | list | None = None
    default_valuation_method: str | None = Field(None, max_length=50)
    auto_create_serial_no: bool | None = None
    default_quality_inspection_template_id: UUID | None = None
    stock_frozen_upto: str | None = Field(None, max_length=50)
    stock_frozen_upto_days: int | None = None
    show_barcode_field: bool | None = None
    convert_item_desc_to_transaction_desc: bool | None = None
    extra_data: dict | None = None


class StockSettingsCreate(StockSettingsBase):
    pass


class StockSettingsUpdate(BaseModel):
    item_naming_by: str | None = Field(None, max_length=50)
    item_naming_series: str | None = Field(None, max_length=100)
    stock_entry_naming_series: str | None = Field(None, max_length=100)
    delivery_note_naming_series: str | None = Field(None, max_length=100)
    purchase_receipt_naming_series: str | None = Field(None, max_length=100)
    default_warehouse_id: UUID | None = None
    allow_negative_stock: bool | None = None
    over_delivery_receipt_allowance: Decimal | float | None = None
    over_billing_allowance: Decimal | float | None = None
    auto_indent: bool | None = None
    auto_indent_notification: dict | list | None = None
    default_valuation_method: str | None = Field(None, max_length=50)
    auto_create_serial_no: bool | None = None
    default_quality_inspection_template_id: UUID | None = None
    stock_frozen_upto: str | None = Field(None, max_length=50)
    stock_frozen_upto_days: int | None = None
    show_barcode_field: bool | None = None
    convert_item_desc_to_transaction_desc: bool | None = None
    extra_data: dict | None = None


class StockSettingsResponse(BaseModel):
    id: UUID
    organization_id: UUID
    item_naming_by: str | None = None
    item_naming_series: str | None = None
    stock_entry_naming_series: str | None = None
    delivery_note_naming_series: str | None = None
    purchase_receipt_naming_series: str | None = None
    default_warehouse_id: UUID | None = None
    allow_negative_stock: bool | None = None
    over_delivery_receipt_allowance: Decimal | None = None
    over_billing_allowance: Decimal | None = None
    auto_indent: bool | None = None
    auto_indent_notification: dict | list | None = None
    default_valuation_method: str | None = None
    auto_create_serial_no: bool | None = None
    default_quality_inspection_template_id: UUID | None = None
    stock_frozen_upto: str | None = None
    stock_frozen_upto_days: int | None = None
    show_barcode_field: bool | None = None
    convert_item_desc_to_transaction_desc: bool | None = None
    extra_data: dict | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)
