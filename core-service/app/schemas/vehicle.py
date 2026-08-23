"""Vehicle arrival schemas for inbound receiving."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class VehicleArrivalCreate(BaseModel):
    """Register a vehicle arrival against one or more ASNs."""

    vehicle_no: str = Field(..., min_length=1, max_length=100)
    driver_name: str | None = Field(None, max_length=255)
    driver_contact: str | None = Field(None, max_length=50)
    transporter: str | None = Field(None, max_length=255)
    warehouse_id: UUID | None = None
    dock: str | None = Field(None, max_length=255)
    asn_order_ids: list[UUID] = []
    notes: str | None = Field(None, max_length=1000)


class VehicleArrivalLinkRequest(BaseModel):
    """Link one or more ASN orders to an existing vehicle arrival."""

    asn_order_ids: list[UUID] = Field(..., min_length=1)


class AsnOrderRef(BaseModel):
    """Minimal ASN reference attached to an arrival."""

    id: UUID
    asn_order_no: str
    status: str | None = None

    model_config = ConfigDict(from_attributes=True)


class VehicleInfo(BaseModel):
    id: UUID
    vehicle_no: str
    driver_name: str | None = None
    driver_contact: str | None = None
    transporter: str | None = None

    model_config = ConfigDict(from_attributes=True)


class VehicleArrivalResponse(BaseModel):
    id: UUID
    organization_id: UUID
    vehicle: VehicleInfo | None = None
    warehouse_id: UUID | None = None
    dock: str | None = None
    status: str
    arrived_at: datetime
    notes: str | None = None
    asn_orders: list[AsnOrderRef] = []
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VehicleArrivalListItem(BaseModel):
    id: UUID
    vehicle_no: str | None = None
    driver_name: str | None = None
    transporter: str | None = None
    warehouse_id: UUID | None = None
    dock: str | None = None
    status: str
    arrived_at: datetime
    asn_order_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class VehicleArrivalListResponse(BaseModel):
    vehicle_arrivals: list[VehicleArrivalListItem]
    pagination: PaginationMeta
