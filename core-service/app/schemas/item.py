"""Item related Pydantic schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class ItemBase(BaseModel):
    """Base item schema with common fields"""
    item_code: str | None = Field(None, max_length=100)
    item_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)

    # Classification
    item_group_id: UUID | None = None
    item_type: str = Field(default="stock")

    # Unit of Measure
    uom: str = Field(default="Nos", max_length=50)
    sku: str | None = Field(None, max_length=100)

    # Stock Settings
    maintain_stock: bool = True
    valuation_method: str = Field(default="FIFO")
    allow_negative_stock: bool = False

    # Variants
    has_variants: bool = False
    variant_of: UUID | None = None
    variant_attributes: dict | None = None

    # Batch and Serial
    has_batch_no: bool = False
    has_serial_no: bool = False
    batch_number_series: str | None = Field(None, max_length=100)
    serial_number_series: str | None = Field(None, max_length=100)

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
    quality_inspection_template: UUID | None = None

    # Tax Templates
    sales_tax_template_id: UUID | None = None
    purchase_tax_template_id: UUID | None = None

    # QR Product link — enables unit-level QR tracking for this item
    qr_product_id: UUID | None = None

    # Brand link and GTIN
    brand_id: UUID | None = None
    gtin: str | None = Field(None, max_length=20)

    # Additional Info
    barcode: str | None = Field(None, max_length=100)
    status: str = Field(default="ACTIVE")
    image_url: str | None = Field(None, max_length=500)
    images: list[str] | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    extra_data: dict | None = None


class ItemCreate(ItemBase):
    """Schema for creating a new item"""

    pass


class ItemUpdate(BaseModel):
    """Schema for updating an item (all fields optional)"""

    item_name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)

    # Classification
    item_group_id: UUID | None = None
    item_type: str | None = None

    # Unit of Measure
    uom: str | None = Field(None, max_length=50)
    sku: str | None = Field(None, max_length=100)

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
    batch_number_series: str | None = Field(None, max_length=100)
    serial_number_series: str | None = Field(None, max_length=100)

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
    quality_inspection_template: UUID | None = None

    # Tax Templates
    sales_tax_template_id: UUID | None = None
    purchase_tax_template_id: UUID | None = None

    # QR Product link
    qr_product_id: UUID | None = None

    # Additional Info
    barcode: str | None = Field(None, max_length=100)
    status: str | None = None
    image_url: str | None = Field(None, max_length=500)
    images: list[str] | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    extra_data: dict | None = None


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
    item_code: str | None = None
    item_name: str
    description: str | None = None

    # Classification
    item_group_id: UUID | None = None
    item_group: ItemGroupInfo | None = None
    item_type: str

    # Unit of Measure
    uom: str

    # Warehouse SKU
    sku: str | None = None

    # Stock Settings
    maintain_stock: bool | None = None
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
    standard_rate: Decimal | None = None
    valuation_rate: Decimal | None = None

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
    quality_inspection_template: UUID | None = None

    # Tax Templates
    sales_tax_template_id: UUID | None = None
    purchase_tax_template_id: UUID | None = None

    # QR Product link
    qr_product_id: UUID | None = None

    # Additional Info
    barcode: str | None = None
    status: str
    image_url: str | None = None
    images: list[str] | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    extra_data: dict | None = None

    # Audit
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ItemListItem(BaseModel):
    """Schema for item in list response (lighter version)"""

    id: UUID
    item_code: str | None = None
    item_name: str
    item_type: str
    uom: str | None = None
    sku: str | None = None
    item_group_id: UUID | None = None
    item_group_name: str | None = None
    standard_rate: Decimal | None = None
    status: str
    maintain_stock: bool | None = None
    barcode: str | None = None
    image_url: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ItemListResponse(BaseModel):
    """Schema for paginated item list response"""

    items: list[ItemListItem]
    pagination: PaginationMeta


# --- Item Picker schemas ---


class ItemPickerStockLevels(BaseModel):
    """Aggregated stock levels for item picker"""

    quantity_on_hand: int = 0
    quantity_reserved: int = 0
    quantity_available: int = 0


class ItemPickerItemGroup(BaseModel):
    """Item group info for item picker"""

    id: UUID
    name: str
    code: str


class TaxBreakupItem(BaseModel):
    """Tax rule in breakup for item picker"""

    rule_name: str
    tax_type: str
    rate: float
    is_compound: bool = False


class ItemPickerTaxInfo(BaseModel):
    """Tax template info for item picker"""

    id: UUID
    template_name: str
    template_code: str
    is_compound: bool = False
    breakup: list[TaxBreakupItem] = Field(default_factory=list)


class ItemPickerItem(BaseModel):
    """Item for picker/dropdown with stock, group, and tax info"""

    id: UUID
    item_code: str | None = None
    item_name: str
    uom: str
    sku: str | None = None
    min_order_qty: int = 1
    max_order_qty: int | None = None
    standard_rate: Decimal | None = None
    stock_levels: ItemPickerStockLevels = Field(default_factory=ItemPickerStockLevels)
    item_group: ItemPickerItemGroup | None = None
    tax_info: ItemPickerTaxInfo | None = None


class ItemPickerListResponse(BaseModel):
    """Response for item picker endpoint"""

    items: list[ItemPickerItem]


# --- SKU Lookup ---


class ItemSkuLookupResponse(BaseModel):
    """Lightweight response for SKU/barcode lookup by mobile app"""

    id: UUID
    item_code: str
    item_name: str
    item_type: str | None = None
    uom: str | None = None
    barcode: str | None = None
    standard_rate: Decimal | None = None
    maintain_stock: bool | None = None
    image_url: str | None = None

    model_config = ConfigDict(from_attributes=True)
