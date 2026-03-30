"""Pydantic schemas for admin organization management."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# ── Create / Update ─────────────────────────────────────────────────

class AdminOrgCreate(BaseModel):
    """Schema for creating a new organization via admin portal."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    display_name: str | None = Field(None, max_length=255)
    description: str | None = None
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=20)
    website: str | None = Field(None, max_length=255)
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)
    organization_type: str = Field(
        default="business",
        pattern=r"^(enterprise|business|startup|individual)$",
    )
    industry: str | None = Field(None, max_length=100)
    base_currency: str = Field(default="USD", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    status: str = Field(
        default="active",
        pattern=r"^(active|inactive|suspended|trial)$",
    )


class AdminOrgUpdate(BaseModel):
    """Schema for partial update of an organization via admin portal."""

    name: str | None = Field(None, min_length=1, max_length=255)
    display_name: str | None = Field(None, max_length=255)
    description: str | None = None
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=20)
    website: str | None = Field(None, max_length=255)
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)
    organization_type: str | None = Field(
        None, pattern=r"^(enterprise|business|startup|individual)$"
    )
    industry: str | None = Field(None, max_length=100)
    base_currency: str | None = Field(None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    status: str | None = Field(None, pattern=r"^(active|inactive|suspended|trial)$")
    is_active: bool | None = None
    settings: dict | None = None
    extra_data: dict | None = None


# ── List / Detail responses ──────────────────────────────────────────

class AdminOrgListItem(BaseModel):
    """Single organization in a paginated list."""

    id: UUID
    name: str
    slug: str
    display_name: str | None = None
    status: str
    organization_type: str
    is_active: bool
    created_at: datetime


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class AdminOrgListResponse(BaseModel):
    """Paginated list of organizations."""

    organizations: list[AdminOrgListItem]
    pagination: PaginationMeta


class AdminOrgDetailResponse(BaseModel):
    """Full organization detail with summary counts."""

    id: UUID
    name: str
    slug: str
    display_name: str | None = None
    description: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    organization_type: str
    industry: str | None = None
    base_currency: str | None = None
    logo_url: str | None = None
    status: str
    is_active: bool
    owner_id: UUID | None = None
    settings: dict | None = None
    extra_data: dict | None = None
    created_at: datetime
    updated_at: datetime | None = None
    # Summary counts
    user_count: int = 0
    invoice_count: int = 0
    payment_total: Decimal = Decimal("0")


# ── Billing response ─────────────────────────────────────────────────

class AdminOrgBillingResponse(BaseModel):
    """Billing / subscription summary for a single organization."""

    organization_id: UUID
    organization_name: str
    on_trial: bool = False
    trial_expiry: datetime | None = None
    paid_until: datetime | None = None
    total_invoiced: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")
    outstanding: Decimal = Decimal("0")
