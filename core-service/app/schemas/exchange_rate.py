"""Exchange Rate related Pydantic schemas"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class ExchangeRateCreate(BaseModel):
    """Schema for creating a new Exchange Rate"""

    from_currency: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    to_currency: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    rate: Decimal = Field(..., gt=0)
    effective_date: date | None = None  # defaults to today


class ExchangeRateUpdate(BaseModel):
    """Schema for updating an Exchange Rate"""

    rate: Decimal = Field(..., gt=0)
    effective_date: date | None = None


class ExchangeRateResponse(BaseModel):
    """Schema for Exchange Rate response"""

    id: UUID
    organization_id: UUID | None = None
    from_currency: str
    to_currency: str
    rate: Decimal
    effective_date: date
    captured_at: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ExchangeRateListResponse(BaseModel):
    """Schema for paginated Exchange Rate list response"""

    exchange_rates: list[ExchangeRateResponse]
    pagination: PaginationMeta
