"""Public QR verification API contracts."""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QRVerificationStatus(str, Enum):
    AUTHENTIC = "authentic"
    VERIFICATION_REQUIRED = "verification_required"
    NOT_ACTIVATED = "not_activated"
    ALREADY_USED = "already_used"
    INVALID = "invalid"


class QRVerificationChannel(str, Enum):
    OVERT = "overt"
    COVERT = "covert"


class PublicQRVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gtin: str = Field(..., min_length=1, max_length=20)
    serial_number: str = Field(..., min_length=1, max_length=75)
    timestamp: str = Field(..., min_length=10, max_length=20)
    signature: str = Field(..., min_length=1, max_length=1024)
    qr_channel: QRVerificationChannel | None = None
    secure_code: str | None = Field(None, min_length=1, max_length=50)

    @field_validator("gtin", "serial_number", "timestamp", "signature")
    @classmethod
    def strip_required_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("signature")
    @classmethod
    def restore_legacy_base64_plus(cls, value: str) -> str:
        """Repair '+' characters decoded as spaces from legacy QR query strings."""
        return value.replace(" ", "+")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("timestamp must contain digits only")
        return value


class PublicQRVerifyResponse(BaseModel):
    verification_status: QRVerificationStatus
    authentic: bool
    message: str
    requires_action: bool = False
    challenge_type: str | None = None
    product_name: str | None = None
    generic_name: str | None = None
    brand_name: str | None = None
    sku_name: str | None = None
    sku_code: str | None = None
    variant_attributes: dict[str, str] = Field(default_factory=dict)
    gtin: str | None = None
    serial_number: str | None = None
    qr_type: str | None = None
    qr_channel: QRVerificationChannel | None = None
    activation_method: str | None = None
    industry: str | None = None
    warranty_period_months: int | None = None
    logo_url: str | None = None
    product_image_url: str | None = None
    banner_image_url: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    website_url: str | None = None
    scan_event_id: UUID | None = None


class PublicScanLocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_meters: int | None = Field(None, ge=0, le=100_000)
