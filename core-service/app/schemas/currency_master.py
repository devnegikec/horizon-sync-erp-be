"""Currency Master related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class CurrencyMasterBase(BaseModel):
    """Base Currency Master schema with common fields"""

    code: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    name: str = Field(..., min_length=1, max_length=100)
    symbol: str | None = Field(None, max_length=5)
    is_base_currency: bool = False


class CurrencyMasterCreate(CurrencyMasterBase):
    """Schema for creating a new Currency"""

    pass


class CurrencyMasterUpdate(BaseModel):
    """Schema for updating a Currency (all fields optional)"""

    name: str | None = Field(None, min_length=1, max_length=100)
    symbol: str | None = Field(None, max_length=5)
    is_base_currency: bool | None = None


class CurrencyMasterResponse(BaseModel):
    """Schema for Currency Master response"""

    id: UUID
    organization_id: UUID
    code: str
    name: str
    symbol: str | None = None
    is_base_currency: bool
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CurrencyMasterListResponse(BaseModel):
    """Schema for paginated Currency Master list response"""

    currencies: list[CurrencyMasterResponse]
    pagination: PaginationMeta
