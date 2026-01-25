"""Item related Pydantic schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class ItemBase(BaseModel):
    """Base item schema with common fields"""

    item_code: str = Field(..., min_length=1, max_length=100)
    item_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

    # Classification
    item_group_id: UUID | None = None
    item_type: str = Field(default="stock")

    # Unit of Measure
    uom: str = Field(default="Nos", max_length=50)

    # Stock Settings
    maintain_stock: bool = True
    valuation_method: str = Field(default="fifo")
    allow_negative_stock: bool = False

    # Variants
    has_variants: bool = False
    variant_of: UUID | None = None
    variant_attributes: dict | None = None

    # Batch and Serial
    has_batch_no: bool = False
    has_serial_no: bool = False
    batch_number_series: str | None = None
    serial_number_series: str | None = None

    # Pricing
    standard_rate: Decimal = Field(default=Decimal("0.00"), ge=0)
    valuation_rate: Decimal = Field(default=Decimal("0.00"), ge=0)

    # Reorder Settings
    enable_auto_reorder: bool = False
    reorder_level: int = Field(default=0, ge=0)
    reorder_qty: int = Field(default=0, ge=0)
    min_order_qty: int = Field(default=1, ge=1)
    max_order_qty: int | None = None

    # Weight
    weight_per_unit: Decimal | None = None
    weight_uom: str | None = None

    # Quality Inspection
    inspection_required_before_purchase: bool = False
    inspection_required_before_delivery: bool = False

    # Additional Info
    barcode: str | None = Field(None, max_length=100)
    status: str = Field(default="active")
    image_url: str | None = Field(None, max_length=500)
    images: list[str] | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None


class ItemCreate(ItemBase):
    """Schema for creating a new item"""

    pass


class ItemUpdate(BaseModel):
    """Schema for updating an item (all fields optional)"""

    item_name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None

    # Classification
    item_group_id: UUID | None = None
    item_type: str | None = None

    # Unit of Measure
    uom: str | None = Field(None, max_length=50)

    # Stock Settings
    maintain_stock: bool | None = None
    valuation_method: str | None = None
    allow_negative_stock: bool | None = None

    # Variants
    has_variants: bool | None = None
    variant_of: UUID | None = None
    variant_attributes: dict | None = None

    # Batch and Serial
    has_batch_no: bool | None = None
    has_serial_no: bool | None = None
    batch_number_series: str | None = None
    serial_number_series: str | None = None

    # Pricing
    standard_rate: Decimal | None = Field(None, ge=0)
    valuation_rate: Decimal | None = Field(None, ge=0)

    # Reorder Settings
    enable_auto_reorder: bool | None = None
    reorder_level: int | None = Field(None, ge=0)
    reorder_qty: int | None = Field(None, ge=0)
    min_order_qty: int | None = Field(None, ge=1)
    max_order_qty: int | None = None

    # Weight
    weight_per_unit: Decimal | None = None
    weight_uom: str | None = None

    # Quality Inspection
    inspection_required_before_purchase: bool | None = None
    inspection_required_before_delivery: bool | None = None

    # Additional Info
    barcode: str | None = Field(None, max_length=100)
    status: str | None = None
    image_url: str | None = Field(None, max_length=500)
    images: list[str] | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None


class ItemGroupInfo(BaseModel):
    """Minimal item group info for nested response"""

    id: UUID
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class ItemResponse(BaseModel):
    """Schema for item response"""

    id: UUID
    organization_id: UUID
    item_code: str
    item_name: str
    description: str | None = None

    # Classification
    item_group_id: UUID | None = None
    item_group: ItemGroupInfo | None = None
    item_type: str

    # Unit of Measure
    uom: str

    # Stock Settings
    maintain_stock: bool
    valuation_method: str
    allow_negative_stock: bool

    # Variants
    has_variants: bool
    variant_of: UUID | None = None
    variant_attributes: dict | None = None

    # Batch and Serial
    has_batch_no: bool
    has_serial_no: bool
    batch_number_series: str | None = None
    serial_number_series: str | None = None

    # Pricing
    standard_rate: Decimal
    valuation_rate: Decimal

    # Reorder Settings
    enable_auto_reorder: bool
    reorder_level: int
    reorder_qty: int
    min_order_qty: int
    max_order_qty: int | None = None

    # Weight
    weight_per_unit: Decimal | None = None
    weight_uom: str | None = None

    # Quality Inspection
    inspection_required_before_purchase: bool
    inspection_required_before_delivery: bool

    # Additional Info
    barcode: str | None = None
    status: str
    image_url: str | None = None
    images: list[str] | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None

    # Audit
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemListItem(BaseModel):
    """Schema for item in list response (lighter version)"""

    id: UUID
    item_code: str
    item_name: str
    item_type: str
    uom: str
    item_group_id: UUID | None = None
    standard_rate: Decimal
    status: str
    maintain_stock: bool
    barcode: str | None = None
    image_url: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemListResponse(BaseModel):
    """Schema for paginated item list response"""

    items: list[ItemListItem]
    pagination: PaginationMeta
