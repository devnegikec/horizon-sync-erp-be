"""Serial number and serial_no_history Pydantic schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta

# ----- SerialNo -----


class SerialNoBase(BaseModel):
    """Base serial number schema"""

    serial_no: str = Field(..., min_length=1, max_length=100)
    item_id: UUID
    warehouse_id: UUID

    status: str | None = Field(None, max_length=50)

    purchase_date: datetime | None = None
    purchase_rate: Decimal | float | None = None
    supplier_id: UUID | None = None

    delivery_date: datetime | None = None
    customer_id: UUID | None = None

    warranty_period: int | None = None
    warranty_expiry_date: datetime | None = None
    amc_expiry_date: datetime | None = None

    batch_no: str | None = Field(None, max_length=100)
    description: str | None = None
    extra_data: dict | None = None


class SerialNoCreate(SerialNoBase):
    """Create serial number"""

    pass


class SerialNoUpdate(BaseModel):
    """Update serial number (all optional)"""

    warehouse_id: UUID | None = None
    status: str | None = Field(None, max_length=50)

    purchase_date: datetime | None = None
    purchase_rate: Decimal | float | None = None
    supplier_id: UUID | None = None
    delivery_date: datetime | None = None
    customer_id: UUID | None = None
    warranty_period: int | None = None
    warranty_expiry_date: datetime | None = None
    amc_expiry_date: datetime | None = None
    batch_no: str | None = Field(None, max_length=100)
    description: str | None = None
    extra_data: dict | None = None


class SerialNoResponse(BaseModel):
    """Serial number response"""

    id: UUID
    organization_id: UUID
    serial_no: str
    item_id: UUID
    warehouse_id: UUID
    status: str | None = None
    purchase_date: datetime | None = None
    purchase_rate: Decimal | None = None
    supplier_id: UUID | None = None
    delivery_date: datetime | None = None
    customer_id: UUID | None = None
    warranty_period: int | None = None
    warranty_expiry_date: datetime | None = None
    amc_expiry_date: datetime | None = None
    batch_no: str | None = None
    description: str | None = None
    extra_data: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SerialNoListItem(BaseModel):
    """Serial number list item"""

    id: UUID
    serial_no: str
    item_id: UUID
    warehouse_id: UUID
    status: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SerialNoListResponse(BaseModel):
    """Paginated serial numbers list"""

    serial_nos: list[SerialNoListItem]
    pagination: PaginationMeta


# ----- SerialNoHistory -----


class SerialNoHistoryCreate(BaseModel):
    """Create history entry"""

    transaction_type: str = Field(..., min_length=1, max_length=50)
    transaction_id: UUID | None = None
    from_warehouse_id: UUID | None = None
    to_warehouse_id: UUID | None = None
    transaction_date: datetime | None = None
    remarks: str | None = None


class SerialNoHistoryResponse(BaseModel):
    """History entry response"""

    id: UUID
    organization_id: UUID
    serial_no_id: UUID
    transaction_type: str
    transaction_id: UUID | None = None
    from_warehouse_id: UUID | None = None
    to_warehouse_id: UUID | None = None
    transaction_date: datetime
    remarks: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
