"""Pydantic schemas for QR Products module"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ── QR Product ────────────────────────────────────────────────────────────────


class QRProductPackagingDetails(BaseModel):
    """Physical packaging details for a product's base packaging unit."""

    unit_name: str = Field("Each", min_length=1, max_length=100)
    conversion_factor: Decimal = Field(Decimal("1"), gt=0)
    items_per_master_pack: int | None = Field(
        None, gt=0, description="Items per master pack (used for QR master pack grouping)"
    )
    length_mm: Decimal | None = Field(None, ge=0)
    width_mm: Decimal | None = Field(None, ge=0)
    height_mm: Decimal | None = Field(None, ge=0)
    weight_grams: Decimal | None = Field(None, ge=0)


class QRProductBase(BaseModel):
    name: str = Field(..., max_length=100)
    sku: str | None = None
    generic_name: str | None = None
    gtin: str | None = None
    industry: str | None = None
    landing_page: str | None = None
    image_url: str | None = None
    banner_image_url: str | None = None
    email: str | None = None
    phone_number: str | None = None
    client_product_auth_url: str | None = None
    activation_method: str = Field("pre", pattern="^(pre|post)$")
    sr_number_type: str | None = None
    redirect_to_client: bool = False
    warranty_period_months: int | None = None
    qr_type: str | None = None
    extra_data: dict[str, Any] | None = None


class QRProductCreate(QRProductBase):
    brand_id: UUID | None = None
    packaging_details: QRProductPackagingDetails | None = None


class QRProductUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    generic_name: str | None = None
    gtin: str | None = None
    industry: str | None = None
    landing_page: str | None = None
    image_url: str | None = None
    banner_image_url: str | None = None
    email: str | None = None
    phone_number: str | None = None
    client_product_auth_url: str | None = None
    activation_method: str | None = Field(None, pattern="^(pre|post)$")
    sr_number_type: str | None = None
    redirect_to_client: bool | None = None
    warranty_period_months: int | None = None
    qr_type: str | None = None
    is_active: bool | None = None
    extra_data: dict[str, Any] | None = None
    packaging_details: QRProductPackagingDetails | None = None


class QRProductResponse(QRProductBase):
    id: UUID
    organization_id: UUID
    brand_id: UUID | None = None
    is_active: bool
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    # Linked inventory item (auto-created when the QR product is created)
    linked_item_id: UUID | None = None
    # Items per master pack, resolved from the linked item's base packaging unit
    items_per_master_pack: int | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        """Populate linked_item_id and items_per_master_pack from the linked item."""
        instance = super().model_validate(obj, *args, **kwargs)
        # SQLAlchemy relationship: qr_product.items is a list
        try:
            items = obj.items  # type: ignore[attr-defined]
            if items:
                item = items[0]
                instance.linked_item_id = item.id
                # Resolve Items per Master Pack from the item's base packaging unit
                for pu in item.packaging_units or []:
                    if pu.is_base_unit:
                        instance.items_per_master_pack = pu.items_per_master_pack
                        break
        except Exception:
            pass
        return instance


class QRProductListItem(BaseModel):
    id: UUID
    name: str
    generic_name: str | None
    gtin: str | None
    industry: str | None
    activation_method: str | None
    qr_type: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class QRProductListResponse(BaseModel):
    products: list[QRProductListItem]
    pagination: dict[str, Any]


# ── QR Block ──────────────────────────────────────────────────────────────────


class QRBlockCreate(BaseModel):
    batch: str = Field(..., max_length=50)
    quantity: int = Field(..., gt=0)
    qr_type: str | None = None
    serial_prefix: str | None = None
    sr_number_type: str | None = None
    cert_type: str | None = None
    size: str | None = None
    colour_desc: str | None = None
    price: int | None = None
    style: str | None = None
    qr_image: bool = False
    manufacture_date: date | None = None
    expiry_date: date | None = None
    master_pack_enabled: bool = False
    master_pack_size: int | None = None
    extra_data: dict[str, Any] | None = None


class QRBlockResponse(BaseModel):
    id: UUID
    organization_id: UUID
    product_id: UUID
    batch: str
    quantity: int
    serial_prefix: str | None
    sr_number_type: str | None
    status: str | None
    task_status: str | None
    task_id: str | None
    qr_image: bool
    manufacture_date: date | None
    expiry_date: date | None
    master_pack_enabled: bool = False
    master_pack_size: int | None = None
    gcs_url: str | None
    download_url: str | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BlockDownloadResponse(BaseModel):
    signed_url: str
    expires_at: datetime


# ── Product Item ──────────────────────────────────────────────────────────────


class ProductItemResponse(BaseModel):
    id: UUID
    organization_id: UUID
    product_id: UUID
    block_id: UUID | None
    serial_number: str
    is_verify: bool
    is_auth: bool
    is_suspicious: bool
    qr_deactive: bool
    scans: int
    scan_date: datetime | None
    destination_market: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductItemListResponse(BaseModel):
    items: list[ProductItemResponse]
    pagination: dict[str, Any]


# ── QR Validate (public endpoint) ─────────────────────────────────────────────


class QRValidateRequest(BaseModel):
    serial_number: str
    # Optional scan metadata
    device_type: str | None = None
    os: str | None = None
    browser: str | None = None
    ip_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None


class QRValidateResponse(BaseModel):
    is_authentic: bool
    is_suspicious: bool
    scans: int
    product_name: str | None
    message: str


# ── QR Activation Parameters ──────────────────────────────────────────────────


class QRActivationParamsCreate(BaseModel):
    product_id: UUID | None = None
    block_id: UUID | None = None
    serial_number: str | None = None
    manufacturing_date: date
    expiry_date: date
    manufacturing_unit: str = Field(..., max_length=100)
    dispatch_batch: str | None = None
    destination_market: str | None = None
    mrp: float | None = None
    currency: str | None = None
    batch_size: int | None = None
    qr_settings: bool = False
    qr_cascade: bool = False
    extra_data: dict[str, Any] | None = None


class QRActivationParamsResponse(QRActivationParamsCreate):
    id: UUID
    organization_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Scan Analytics ────────────────────────────────────────────────────────────


class ScanAnalyticsResponse(BaseModel):
    total_scans: int
    unique_serials: int
    suspicious_count: int
    scans_by_country: list[dict[str, Any]]
    scans_by_day: list[dict[str, Any]]


# ── QR Authentication (public endpoint) ───────────────────────────────────────


class AuthenticateRequest(BaseModel):
    serial_number: str
    nonce: str  # timestamp
    cipher: str  # base64 signature


class AuthenticateResponse(BaseModel):
    message: str
    authentic: bool
    product_name: str | None = None
    brand_name: str | None = None
    gtin: str | None = None
    serial_number: str | None = None


# ── Org-Level Block List ───────────────────────────────────────────────────────


class OrgBlockListItem(BaseModel):
    id: UUID
    organization_id: UUID
    product_id: UUID
    product_name: str | None
    batch: str
    quantity: int
    serial_prefix: str | None
    sr_number_type: str | None
    status: str | None
    task_status: str | None
    task_id: str | None
    qr_image: bool
    manufacture_date: date | None
    expiry_date: date | None
    gcs_url: str | None
    download_url: str | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrgBlockListResponse(BaseModel):
    blocks: list[OrgBlockListItem]
    pagination: dict[str, Any]
