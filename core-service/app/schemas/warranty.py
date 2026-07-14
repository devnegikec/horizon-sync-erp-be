"""Pydantic schemas for Warranty module"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ── Warranty Period ───────────────────────────────────────────────────────────


class WarrantyPeriodCreate(BaseModel):
    months: int = Field(..., gt=0)
    is_active: bool = True
    is_default: bool = False


class WarrantyPeriodResponse(WarrantyPeriodCreate):
    id: UUID
    organization_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Warranty Registration ─────────────────────────────────────────────────────


class WarrantyRegisterRequest(BaseModel):
    serial_number: str = Field(..., max_length=120)
    customer_name: str = Field(..., max_length=255)
    mobile: str = Field(..., max_length=255)
    email: str | None = None
    location: str | None = None
    ip: str | None = None
    purchase_date: date | None = None
    extra_data: dict[str, Any] | None = None


class WarrantyResponse(BaseModel):
    id: UUID
    organization_id: UUID
    serial_number: str | None
    customer_name: str
    mobile: str
    email: str | None
    location: str | None
    purchase_date: date | None
    warranty_valid_till: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WarrantyListResponse(BaseModel):
    warranties: list[WarrantyResponse]
    pagination: dict[str, Any]


# ── Warranty Check ────────────────────────────────────────────────────────────


class WarrantyCheckResponse(BaseModel):
    found: bool
    is_valid: bool
    warranty_id: UUID | None
    serial_number: str | None
    customer_name: str | None
    purchase_date: date | None
    warranty_valid_till: datetime | None
    days_remaining: int | None
    message: str
