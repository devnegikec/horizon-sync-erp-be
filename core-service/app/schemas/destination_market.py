"""Pydantic schemas for Destinations module"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DestinationMarketCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20, description="Short market code, e.g. IN, US-WEST")
    country: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    currency_code: str | None = Field(None, max_length=3, description="ISO 4217 code")
    language: str | None = Field(None, max_length=10, description="BCP-47 tag, e.g. en-US")
    tax_rate: Decimal | None = Field(None, ge=0, le=1, description="e.g. 0.18 for 18%")
    is_active: bool = True
    notes: str | None = None
    extra_data: dict[str, Any] | None = None


class DestinationMarketUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    region: str | None = None
    currency_code: str | None = None
    language: str | None = None
    tax_rate: Decimal | None = None
    is_active: bool | None = None
    notes: str | None = None
    extra_data: dict[str, Any] | None = None


class CurrencyInfo(BaseModel):
    code: str
    name: str
    symbol: str | None

    model_config = {"from_attributes": True}


class DestinationMarketResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    code: str
    country: str | None
    region: str | None
    currency_code: str | None
    language: str | None
    tax_rate: Decimal | None
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
    # Enriched currency info (populated by service when available)
    currency: CurrencyInfo | None = None

    model_config = {"from_attributes": True}


class DestinationMarketListResponse(BaseModel):
    markets: list[DestinationMarketResponse]
    pagination: dict[str, Any]


class DestinationCurrencyResponse(BaseModel):
    """Currency details for a specific destination market"""
    market_id: UUID
    market_code: str
    market_name: str
    currency_code: str | None
    currency_name: str | None
    currency_symbol: str | None
    exchange_rate_to_base: Decimal | None = None
