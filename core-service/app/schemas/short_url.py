"""Pydantic schemas for URL Management module"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ShortURLCreate(BaseModel):
    original_url: str = Field(..., description="The full destination URL")
    title: str | None = Field(None, max_length=255)
    slug: str | None = Field(
        None,
        max_length=20,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Custom slug. Auto-generated if omitted.",
    )
    product_id: UUID | None = None
    product_item_id: UUID | None = None
    expires_at: datetime | None = None
    extra_data: dict[str, Any] | None = None


class ShortURLUpdate(BaseModel):
    original_url: str | None = None
    title: str | None = None
    is_active: bool | None = None
    expires_at: datetime | None = None
    extra_data: dict[str, Any] | None = None


class ShortURLResponse(BaseModel):
    id: UUID
    organization_id: UUID
    slug: str
    original_url: str
    title: str | None
    product_id: UUID | None
    product_item_id: UUID | None
    click_count: int
    is_active: bool
    expires_at: datetime | None
    created_at: datetime
    short_url: str  # computed full short URL

    model_config = {"from_attributes": True}


class ShortURLListResponse(BaseModel):
    urls: list[ShortURLResponse]
    pagination: dict[str, Any]


class ResolveURLResponse(BaseModel):
    slug: str
    original_url: str
    click_count: int
    is_active: bool
    expires_at: datetime | None
