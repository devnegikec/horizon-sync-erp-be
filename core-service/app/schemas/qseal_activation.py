"""Schemas for the QSeal activation administration and mobile APIs."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ActivationSettingsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    dispatch_batch: str = Field(min_length=1, max_length=100)
    batch_size: int = Field(gt=0)
    manufacturing_date: date
    manufacturing_unit: str = Field(min_length=1, max_length=100)
    destination_market: str = Field(min_length=1, max_length=100)
    mrp: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    append_to_existing: bool = False


class ActivationSettingsResponse(BaseModel):
    id: UUID
    product_id: UUID
    dispatch_batch: str | None
    batch_size: int | None
    manufacturing_date: date
    manufacturing_unit: str
    destination_market: str | None
    currency: str | None
    mrp: Decimal | None
    expiry_date: date
    history: bool
    created_on: datetime

    model_config = {"from_attributes": True}


class ActivationSummaryResponse(BaseModel):
    product_id: UUID
    activation_method: str | None
    total_blocks: int
    activated_blocks: int
    available_blocks: int
    activation_percentage: float
    current_settings: ActivationSettingsResponse | None


class ActivationSettingsSaveResponse(BaseModel):
    message: str
    settings_id: UUID
    expiry_date: date
    currency: str | None


class ActivationSettingsHistoryResponse(BaseModel):
    items: list[ActivationSettingsResponse]
    page: int
    page_size: int
    total: int


class ActivationScanRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    url: str | None = None
    serial_number: str | None = None
    product_id: UUID | None = None

    @model_validator(mode="after")
    def require_serial_or_url(self):
        if not self.url and not self.serial_number:
            raise ValueError("url or serial_number is required")
        return self


class ActivationScanResponse(BaseModel):
    valid: bool
    serial_number: str
    product_id: UUID
    status: str
    message: str


class SerialActivationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: UUID
    serial_numbers: list[str] = Field(min_length=1, max_length=500)
    settings_id: UUID | None = None
    idempotency_key: str | None = Field(default=None, max_length=100)

    @field_validator("serial_numbers")
    @classmethod
    def validate_serial_numbers(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("serial_numbers cannot contain blank values")
        if len(set(normalized)) != len(normalized):
            raise ValueError("serial_numbers must be unique")
        return normalized

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("idempotency_key cannot be blank")
        return value


class SerialActivationResponse(BaseModel):
    message: str
    product_id: UUID
    activated_count: int
    already_activated_count: int
    product_activated_total: int
    serial_numbers: list[str]


class MobileCurrencyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class MobileCurrencyResponse(BaseModel):
    currency: str | None


class MobileExpiryResponse(BaseModel):
    expiry_date: date


class MobileExpiryRequest(BaseModel):
    product_id: UUID
    manufacturing_date: date


class MobileScanRequest(BaseModel):
    url: str = Field(min_length=1, max_length=600)
    serialNumbers: str | None = Field(default=None, max_length=4000)


class MobileScanResponse(BaseModel):
    message: str
    sr_number: str | None = None
    product_id: UUID | None = None


class MobileActivationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    # ``srnumber`` is the field used by the Django mobile client.
    srnumber: str | None = Field(default=None, max_length=40000)
    product_id: UUID | None = None
    serial_numbers: list[str] | None = Field(default=None, max_length=500)
    idempotency_key: str | None = Field(default=None, max_length=100)

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("idempotency_key cannot be blank")
        return value

    @model_validator(mode="after")
    def require_serials(self):
        if not self.srnumber and not self.serial_numbers:
            raise ValueError("srnumber or serial_numbers is required")
        return self


class MobileSettingsRequest(BaseModel):
    product: UUID
    manufacturing_date: date
    manufacturing_unit: str = Field(min_length=1, max_length=100)
    dispatch_batch: str = Field(min_length=1, max_length=100)
    batch_size: int = Field(gt=0)
    destination_market: str = Field(min_length=1, max_length=100)
    mrp: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    append_to_existing: bool = False

    @model_validator(mode="before")
    @classmethod
    def accept_django_nested_payload(cls, values):
        if isinstance(values, dict) and isinstance(values.get("product"), dict):
            nested = dict(values["product"])
            nested["product"] = nested.get("product") or nested.get("product_id")
            return nested
        return values
