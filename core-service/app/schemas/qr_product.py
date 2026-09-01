"""Pydantic schemas for QR Products module"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

# ── QR Product ────────────────────────────────────────────────────────────────


class QRProductPackagingDetails(BaseModel):
    """Physical packaging details for a product's base packaging unit."""

    unit_name: str = Field("Each", min_length=1, max_length=100)
    conversion_factor: Decimal = Field(Decimal("1"), gt=0)
    items_per_master_pack: int | None = Field(
        None,
        gt=0,
        description="Items per master pack (used for QR master pack grouping)",
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
    shelf_life_setting_id: UUID | None = None
    serial_prefix_setting_id: UUID | None = None
    qr_type: str | None = None
    extra_data: dict[str, Any] | None = None


class QRProductCreate(QRProductBase):
    brand_id: UUID | None = None
    shelf_life_setting_id: UUID
    serial_prefix_setting_id: UUID
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
    shelf_life_setting_id: UUID | None = None
    serial_prefix_setting_id: UUID | None = None
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
    serial_prefix: str | None = None

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
    sku: str | None = None
    generic_name: str | None
    gtin: str | None
    industry: str | None
    activation_method: str | None
    sr_number_type: str | None
    serial_prefix_setting_id: UUID | None
    serial_prefix: str | None
    qr_type: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class QRProductListResponse(BaseModel):
    products: list[QRProductListItem]
    pagination: dict[str, Any]


class QRProductImageResponse(BaseModel):
    image_type: Literal["logo", "banner"]
    url: str | None


# ── QR Block ──────────────────────────────────────────────────────────────────


class QRType(str, Enum):
    DYNAMIC = "dynamic"
    STATIC = "static"
    DUAL = "dual"
    SECURE_CODE = "secure_code"
    ONE_TIME = "one_time"
    POST_ACTIVATION = "post_activation"


class SerialNumberType(str, Enum):
    R8DAN = "R8DAN"
    R6DAN = "R6DAN"
    R4DAN = "R4DAN"
    S8DN = "S8DN"
    S10DN = "S10DN"


_LEGACY_QR_TYPES = {
    "C": QRType.DYNAMIC,
    "D": QRType.DYNAMIC,
    "S": QRType.STATIC,
    "B": QRType.DUAL,
    "SC": QRType.SECURE_CODE,
    "O": QRType.ONE_TIME,
    "N": QRType.POST_ACTIVATION,
}

_LEGACY_SERIAL_TYPES = {
    "RANDOM_8_ALPHA_NUMERIC": SerialNumberType.R8DAN,
    "RANDOM_6_ALPHA_NUMERIC": SerialNumberType.R6DAN,
    "RANDOM_4_ALPHA_NUMERIC": SerialNumberType.R4DAN,
    "SEQUENTIAL_8_DIGIT": SerialNumberType.S8DN,
    "SEQUENTIAL_10_DIGIT": SerialNumberType.S10DN,
}


def normalize_qr_type(value: str | QRType | None) -> QRType | None:
    if value is None or isinstance(value, QRType):
        return value
    normalized = value.strip()
    if not normalized:
        return None
    legacy = _LEGACY_QR_TYPES.get(normalized.upper())
    if legacy:
        return legacy
    try:
        return QRType(normalized.lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in QRType)
        raise ValueError(f"QR type must be one of: {allowed}") from exc


def normalize_serial_number_type(
    value: str | SerialNumberType | None,
) -> SerialNumberType | None:
    if value is None or isinstance(value, SerialNumberType):
        return value
    normalized = value.strip()
    if not normalized:
        return None
    legacy = _LEGACY_SERIAL_TYPES.get(normalized.upper())
    if legacy:
        return legacy
    try:
        return SerialNumberType(normalized.upper())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in SerialNumberType)
        raise ValueError(f"Serial number type must be one of: {allowed}") from exc


class QRBlockCreate(BaseModel):
    batch: str = Field(..., max_length=50)
    quantity: int = Field(..., ge=1, le=5000)
    sku_id: UUID | None = None
    qr_type: QRType | None = None
    channel_setting_id: UUID | None = None
    destination_setting_id: UUID | None = None
    serial_prefix: str | None = Field(None, max_length=20)
    starting_serial: str | None = None
    sr_number_type: SerialNumberType | None = None
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

    @field_validator("batch")
    @classmethod
    def validate_batch(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Batch is required")
        return value

    @field_validator("serial_prefix")
    @classmethod
    def normalize_serial_prefix(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().strip("-")
        return value or None

    @field_validator("qr_type", mode="before")
    @classmethod
    def validate_qr_type(cls, value):
        return normalize_qr_type(value)

    @field_validator("sr_number_type", mode="before")
    @classmethod
    def validate_serial_type(cls, value):
        return normalize_serial_number_type(value)

    @model_validator(mode="after")
    def validate_generation_options(self):
        if self.qr_type == QRType.STATIC:
            if self.quantity != 1:
                raise ValueError("Static QR generation requires quantity=1")
            if self.starting_serial is not None:
                raise ValueError("starting_serial is not valid for Static QR")
            return self

        if self.sr_number_type in {
            SerialNumberType.S8DN,
            SerialNumberType.S10DN,
        }:
            if self.starting_serial is None:
                raise ValueError(
                    "starting_serial is required for sequential serial numbers"
                )
            if not self.starting_serial.isdigit():
                raise ValueError("starting_serial must contain digits only")
            max_length = 8 if self.sr_number_type == SerialNumberType.S8DN else 10
            if len(self.starting_serial) > max_length:
                raise ValueError(f"starting_serial must be at most {max_length} digits")
        elif self.sr_number_type is not None and self.starting_serial is not None:
            raise ValueError(
                "starting_serial is only valid for sequential serial numbers"
            )
        return self


class QRBlockResponse(BaseModel):
    id: UUID
    organization_id: UUID
    product_id: UUID
    sku_id: UUID | None = None
    batch: str
    quantity: int
    qr_type: QRType | None = None
    channel_setting_id: UUID | None = None
    destination_setting_id: UUID | None = None
    distribution_channel: str | None = None
    destination_market: str | None = None
    serial_prefix: str | None
    starting_serial: str | None = None
    sr_number_type: str | None
    status: str | None
    task_status: str | None
    task_id: str | None
    qr_image: bool
    generated_count: int = 0
    progress: int = 0
    error_code: str | None = None
    error_message: str | None = None
    manufacture_date: date | None
    expiry_date: date | None
    master_pack_enabled: bool = False
    master_pack_size: int | None = None
    gcs_url: str | None
    download_url: str | None
    download_available: bool = False
    artifact_generated_at: datetime | None = None
    activation_status: (
        Literal["activated", "deactivated", "partially_activated"] | None
    ) = None
    activated_count: int = 0
    deactivated_count: int = 0
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
    qr_active: bool
    scans: int
    scan_count: int = 0
    scan_date: datetime | None
    last_scanned_at: datetime | None = None
    secret_code: str | None = Field(None, validation_alias="secrete_code")
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
    sku_id: UUID | None = None
    product_name: str | None
    batch: str
    quantity: int
    qr_type: QRType | None = None
    channel_setting_id: UUID | None = None
    destination_setting_id: UUID | None = None
    distribution_channel: str | None = None
    destination_market: str | None = None
    serial_prefix: str | None
    starting_serial: str | None = None
    sr_number_type: str | None
    status: str | None
    task_status: str | None
    task_id: str | None
    qr_image: bool
    generated_count: int = 0
    progress: int = 0
    error_code: str | None = None
    error_message: str | None = None
    manufacture_date: date | None
    expiry_date: date | None
    gcs_url: str | None
    download_url: str | None
    download_available: bool = False
    artifact_generated_at: datetime | None = None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrgBlockListResponse(BaseModel):
    blocks: list[OrgBlockListItem]
    pagination: dict[str, Any]
