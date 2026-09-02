"""Advance Stock Notice (ASN) Order schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class AsnOrderWarehouseInfo(BaseModel):
    """Minimal warehouse info used in list/detail responses"""

    id: UUID
    name: str
    code: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AsnOrderVehicleArrivalInfo(BaseModel):
    """Vehicle arrival information linked to an ASN order."""

    id: UUID
    vehicle_no: str | None = None
    driver_name: str | None = None
    driver_contact: str | None = None
    transporter: str | None = None
    dock: str | None = None
    status: str
    arrived_at: datetime


class AsnOrderItemBase(BaseModel):
    item_id: UUID
    qty: Decimal | float = Field(..., gt=0)
    uom: str = Field(..., min_length=1, max_length=50)
    sort_order: int = 0
    serial_nos: list[str] | None = None


class AsnOrderItemCreate(AsnOrderItemBase):
    """Schema for creating an ASN order item"""


class AsnOrderItemResponse(AsnOrderItemBase):
    id: UUID
    organization_id: UUID
    asn_order_id: UUID
    item_code: str | None = None
    item_name: str | None = None
    sku: str | None = None
    delivered_qty: Decimal | float = 0
    shipped_qty: Decimal | float = 0
    received_qty: Decimal | float = 0
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AsnOrderTransferProgress(BaseModel):
    """Serial-level transfer progress for internal-transfer ASNs."""

    total_serials: int
    received_serials: int
    in_transit_serials: int


class AsnOrderBase(BaseModel):
    asn_order_no: str | None = Field(None, min_length=1, max_length=100)
    warehouse_id_from: UUID | None = None
    warehouse_id_to: UUID | None = None
    order_date: datetime
    delivery_date: datetime | None = None
    status: str = Field(
        default="draft",
        pattern="^(draft|confirmed|partially_delivered|delivered|closed|cancelled)$",
    )
    grand_total: Decimal | float = 0
    reference_type: str | None = None
    reference_id: UUID | None = None
    reference_no: str | None = None
    asn_type: str | None = Field(
        None, pattern="^(purchase|internal_transfer|stock_receipt)$"
    )
    remarks: str | None = Field(None, max_length=1000)


class AsnOrderCreate(AsnOrderBase):
    items: list[AsnOrderItemCreate] = []


class AsnOrderUpdate(BaseModel):
    warehouse_id_from: UUID | None = None
    warehouse_id_to: UUID | None = None
    order_date: datetime | None = None
    delivery_date: datetime | None = None
    status: str | None = Field(
        None,
        pattern="^(draft|confirmed|partially_delivered|delivered|closed|cancelled)$",
    )
    asn_type: str | None = Field(
        None, pattern="^(purchase|internal_transfer|stock_receipt)$"
    )
    remarks: str | None = Field(None, max_length=1000)
    items: list[AsnOrderItemCreate] | None = None


class AsnOrderResponse(AsnOrderBase):
    id: UUID
    organization_id: UUID
    from_warehouse: AsnOrderWarehouseInfo | None = None
    to_warehouse: AsnOrderWarehouseInfo | None = None
    vehicle_arrivals: list[AsnOrderVehicleArrivalInfo] = []
    submitted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    linked_pick_list_id: UUID | None = None
    linked_pick_list_no: str | None = None
    transfer_progress: AsnOrderTransferProgress | None = None
    created_at: datetime
    updated_at: datetime
    items: list[AsnOrderItemResponse] = []
    model_config = ConfigDict(from_attributes=True)


class AsnOrderListItem(BaseModel):
    id: UUID
    organization_id: UUID
    asn_order_no: str
    status: str
    order_date: datetime
    delivery_date: datetime | None = None
    grand_total: Decimal | float = 0
    asn_type: str | None = None
    linked_pick_list_id: UUID | None = None
    from_warehouse: AsnOrderWarehouseInfo | None = None
    to_warehouse: AsnOrderWarehouseInfo | None = None
    vehicle_arrivals: list[AsnOrderVehicleArrivalInfo] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AsnOrderListResponse(BaseModel):
    asn_orders: list[AsnOrderListItem]
    pagination: PaginationMeta


class AsnOrderStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        pattern="^(draft|confirmed|partially_delivered|delivered|closed|cancelled)$",
    )
