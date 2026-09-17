"""Stock entry and stock_entry_items schemas"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.stock_entry import StockEntry

from app.schemas.common import PaginationMeta

_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_ASN_PREFIXED_RE = re.compile(
    r"\bASN\s+([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\b",
    re.IGNORECASE,
)


def _resolve_asn_numbers_in_remarks(remarks: str | None, db) -> str | None:
    """Replace ASN order UUIDs in remarks with their human-readable numbers.

    Stock entries auto-created from receiving slips embed the ASN order UUID
    in remarks (e.g. "ASN 6c41edae-..."). Resolve those UUIDs to
    ``asn_order_no`` for display. Non-ASN UUIDs are left untouched.
    """
    if not remarks or db is None:
        return remarks

    from app.models.asn_order import AsnOrder

    def _number_for_uuid(uuid_str: str) -> str | None:
        try:
            asn = db.get(AsnOrder, UUID(uuid_str))
        except Exception:
            return None
        return asn.asn_order_no if asn is not None else None

    # Replace "ASN <uuid>" with the ASN number (which already carries the
    # "ASN-" prefix), avoiding a doubled "ASN ASN-" in the output.
    def _asn_prefixed(match: re.Match) -> str:
        num = _number_for_uuid(match.group(1))
        return num if num else match.group(0)

    remarks = _ASN_PREFIXED_RE.sub(_asn_prefixed, remarks)

    # Replace any remaining bare UUIDs that resolve to an ASN number.
    def _bare(match: re.Match) -> str:
        num = _number_for_uuid(match.group(0))
        return num if num else match.group(0)

    return _UUID_RE.sub(_bare, remarks)


def _resolve_source_warehouse(e: StockEntry, db) -> WarehouseInfo | None:
    """Resolve the source (from) warehouse for entries created from receiving
    slips when it was not copied onto the stock entry directly.

    The ASN → receiving slip → stock entry flow stores only the destination
    warehouse on the entry. The source warehouse is recoverable via the chain:
    ``stock_entry.reference_id → receiving_slips → asn_orders.warehouse_id_from``.
    """
    if e.from_warehouse_id is not None or db is None:
        return None
    if e.reference_type != "receiving_slip" or e.reference_id is None:
        return None

    try:
        from app.models.asn_order import AsnOrder
        from app.models.receiving_slip import ReceivingSlip
        from app.models.warehouse import Warehouse

        slip = db.get(ReceivingSlip, e.reference_id)
        if slip is None or slip.asn_order_id is None:
            return None
        asn = db.get(AsnOrder, slip.asn_order_id)
        if asn is None or asn.warehouse_id_from is None:
            return None
        wh = db.get(Warehouse, asn.warehouse_id_from)
        if wh is None:
            return None
        return WarehouseInfo(name=wh.name, code=wh.code)
    except Exception:
        return None


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
    total_value: Decimal | None = None
    remarks: str | None = None
    created_at: datetime
    from_warehouse: WarehouseInfo | None = None
    to_warehouse: WarehouseInfo | None = None

    model_config = ConfigDict(from_attributes=True)


class StockEntryListResponse(BaseModel):
    stock_entries: list[StockEntryListItem]
    pagination: PaginationMeta


def stock_entry_to_list_item(e: StockEntry, db=None) -> StockEntryListItem:
    """Build list item from ORM without embedding warehouses (avoids lazy-load loops)."""

    from_warehouse = None
    if getattr(e, "from_warehouse", None) is not None:
        from_warehouse = WarehouseInfo(
            name=e.from_warehouse.name, code=e.from_warehouse.code
        )
    elif db is not None:
        from_warehouse = _resolve_source_warehouse(e, db)
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
        total_value=e.total_value
        if e.total_value is not None
        else getattr(e, "_computed_total_value", None),
        remarks=_resolve_asn_numbers_in_remarks(e.remarks, db),
        created_at=e.created_at,
        from_warehouse=from_warehouse,
        to_warehouse=to_warehouse,
    )


def stock_entry_to_response(e: StockEntry, db=None) -> StockEntryResponse:
    """Build response from ORM without embedding warehouses (avoids lazy-load loops)."""

    from_warehouse = None
    if getattr(e, "from_warehouse", None) is not None:
        from_warehouse = WarehouseInfo(
            name=e.from_warehouse.name, code=e.from_warehouse.code
        )
    elif db is not None:
        from_warehouse = _resolve_source_warehouse(e, db)
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
                # Fallback: when no explicit rate/amount was stored, derive the
                # display amount from the item's standard rate so line-item
                # amounts and totals are not shown as zero.
                if (item_resp.basic_rate is None or item_resp.basic_rate == 0) and (
                    item_resp.basic_amount is None or item_resp.basic_amount == 0
                ):
                    std_rate = item.item.standard_rate
                    if std_rate is not None and std_rate != 0:
                        item_resp.basic_rate = std_rate
                        item_resp.basic_amount = Decimal(str(std_rate)) * Decimal(
                            str(item_resp.qty or 0)
                        )
            items.append(item_resp)

    total_value = e.total_value
    if total_value is None:
        amounts = [it.basic_amount for it in items if it.basic_amount is not None]
        total_value = sum(amounts, Decimal("0")) if amounts else None

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
        remarks=_resolve_asn_numbers_in_remarks(e.remarks, db),
        total_value=total_value,
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
