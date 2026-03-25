"""Pydantic schemas for Brand management"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BrandCreate(BaseModel):
    name: str = Field(..., max_length=256)
    short_code: str = Field(..., max_length=256)


class BrandUpdate(BaseModel):
    name: str | None = Field(None, max_length=256)
    short_code: str | None = Field(None, max_length=256)


class BrandResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    short_code: str
    public_key: str
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    # private_key_encrypted is NEVER included

    model_config = ConfigDict(from_attributes=True)


class BrandListResponse(BaseModel):
    brands: list[BrandResponse]
    pagination: dict[str, Any]
