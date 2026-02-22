"""Smart Picking schemas — suggest allocation, create pick list, create delivery note"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── Suggest Allocation ──────────────────────────────────────────────


class AllocationSuggestionItem(BaseModel):
    """Single warehouse allocation suggestion for one item."""

    item_id: UUID
    item_code: str
    item_name: str
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    suggested_qty: Decimal
    current_available: int
    quantity_reserved: int
    uom: str


class AllocationSuggestionResponse(BaseModel):
    """Full allocation suggestion for a sales order."""

    sales_order_id: UUID
    sales_order_no: str
    customer_id: UUID
    suggestions: list[AllocationSuggestionItem]
    unallocated: list[dict] = Field(
        default_factory=list,
        description="Items (or partial qty) that could not be allocated due to insufficient stock",
    )


# ── Create Smart Pick List ─────────────────────────────────────────


class SmartPickAllocation(BaseModel):
    item_id: UUID
    warehouse_id: UUID
    qty: Decimal = Field(..., gt=0)
    uom: str = Field(..., min_length=1, max_length=50)


class SmartPickListCreate(BaseModel):
    sales_order_id: UUID
    allocations: list[SmartPickAllocation] = Field(..., min_length=1)
    remarks: str | None = None


class SmartPickListResponse(BaseModel):
    id: UUID
    pick_list_no: str
    status: str
    sales_order_id: UUID
    sales_order_no: str
    items: list[dict]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Delivery Note from Pick List ───────────────────────────────────


class DeliveryNoteFromPickListRequest(BaseModel):
    pick_list_id: UUID
    delivery_date: datetime | None = None
    remarks: str | None = None


class DeliveryNoteFromPickListResponse(BaseModel):
    id: UUID
    delivery_note_no: str
    customer_id: UUID
    status: str
    pick_list_id: UUID
    items: list[dict]
    stock_movements_created: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
