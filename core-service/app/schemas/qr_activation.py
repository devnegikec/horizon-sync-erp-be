"""Pydantic schemas for Landing / Public API module"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Destination Market ────────────────────────────────────────────────────────

class DestinationMarketResponse(BaseModel):
    id: UUID
    name: str
    code: str
    country: str | None = None
    currency: str | None = Field(default=None, alias="currency_code")
    is_active: bool

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

class DestinationMarketListResponse(BaseModel):
    markets: list[DestinationMarketResponse]
    pagination: dict[str, Any]


class CurrencyByMarketRequest(BaseModel):
    name: str


class CurrencyByMarketResponse(BaseModel):
    currency: str




# ── Product Expiry ────────────────────────────────────────────────────────────

class ProductExpiryRequest(BaseModel):
    product_id: UUID
    manufacturing_date: date


class ProductExpiryResponse(BaseModel):
    expiry_date: date


# ── QR Scan ───────────────────────────────────────────────────────────────────

class QRScanRequest(BaseModel):
    url: str
    serialNumbers: str | None = None  # comma-separated existing activated serials


class QRScanResponse(BaseModel):
    message: str
    sr_number: str | None = None
    product_id: UUID | None = None


# ── Product Activation ────────────────────────────────────────────────────────

class ProductActivationRequest(BaseModel):
    srnumber: str  # comma-separated serial numbers


class ProductActivationResponse(BaseModel):
    message: str


# ── QR Settings ──────────────────────────────────────────────────────────────

class QRSettingsCreateRequest(BaseModel):
    product: UUID
    manufacturing_date: date
    manufacturing_unit: str = Field(..., max_length=100)
    dispatch_batch: str
    batch_size: int
    destination_market: str
    mrp: float
    append_to_existing: bool | None = None


class QRSettingsResponse(BaseModel):
    manufacturing_date: date
    manufacturing_unit: str
    expiry_date: date
    mrp: float
    destination_market: str
    dispatch_batch: str
    batch_size: int
    currency: str
    prefix: str | None = None