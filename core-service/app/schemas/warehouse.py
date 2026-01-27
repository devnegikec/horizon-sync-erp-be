"""Warehouse related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class WarehouseBase(BaseModel):
    """Base warehouse schema with common fields"""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None

    # Hierarchy
    parent_warehouse_id: UUID | None = None
    warehouse_type: str = Field(default="warehouse")

    # Address
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)

    # Contact
    contact_name: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=50)
    contact_email: str | None = Field(None, max_length=255)

    # Capacity
    total_capacity: int | None = Field(None, ge=0)
    capacity_uom: str | None = Field(None, max_length=50)

    # Accounting
    stock_account_id: UUID | None = None

    # Status
    is_active: bool = True
    is_default: bool = False

    # Extra
    extra_data: dict | None = None


class WarehouseCreate(WarehouseBase):
    """Schema for creating a new warehouse"""

    pass


class WarehouseUpdate(BaseModel):
    """Schema for updating a warehouse (all fields optional)"""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None

    # Hierarchy
    parent_warehouse_id: UUID | None = None
    warehouse_type: str | None = None

    # Address
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)

    # Contact
    contact_name: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=50)
    contact_email: str | None = Field(None, max_length=255)

    # Capacity
    total_capacity: int | None = Field(None, ge=0)
    capacity_uom: str | None = Field(None, max_length=50)

    # Accounting
    stock_account_id: UUID | None = None

    # Status
    is_active: bool | None = None
    is_default: bool | None = None

    # Extra
    extra_data: dict | None = None


class WarehouseParentInfo(BaseModel):
    """Minimal warehouse info for nested response (parent reference)"""

    id: UUID
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class WarehouseResponse(BaseModel):
    """Schema for warehouse response"""

    id: UUID
    organization_id: UUID
    name: str
    code: str
    description: str | None = None

    # Hierarchy
    parent_warehouse_id: UUID | None = None
    parent: WarehouseParentInfo | None = None
    warehouse_type: str

    # Address
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None

    # Contact
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None

    # Capacity
    total_capacity: int | None = None
    capacity_uom: str | None = None

    # Accounting
    stock_account_id: UUID | None = None

    # Status
    is_active: bool
    is_default: bool

    # Extra
    extra_data: dict | None = None

    # Audit
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseListItem(BaseModel):
    """Schema for warehouse in list response (lighter version)"""

    id: UUID
    name: str
    code: str
    warehouse_type: str
    parent_warehouse_id: UUID | None = None
    city: str | None = None
    is_active: bool
    is_default: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseListResponse(BaseModel):
    """Schema for paginated warehouse list response"""

    warehouses: list[WarehouseListItem]
    pagination: PaginationMeta


class WarehouseTreeNode(BaseModel):
    """Schema for warehouse in tree structure"""

    id: UUID
    name: str
    code: str
    warehouse_type: str
    is_active: bool
    is_default: bool
    children: list["WarehouseTreeNode"] = []

    model_config = ConfigDict(from_attributes=True)


# Update forward reference for recursive type
WarehouseTreeNode.model_rebuild()
