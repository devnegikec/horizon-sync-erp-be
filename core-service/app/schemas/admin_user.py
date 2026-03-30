"""Pydantic schemas for admin user management."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.admin_organization import PaginationMeta


# ── Role enum ────────────────────────────────────────────────────────

class AllowedRole(str, Enum):
    system_admin = "system_admin"
    org_admin = "org_admin"
    user = "user"


# ── Create / Update ─────────────────────────────────────────────────

class AdminUserCreate(BaseModel):
    """Schema for creating a new user via admin portal."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    organization_id: UUID
    roles: list[AllowedRole] = Field(default=[AllowedRole.user])
    phone: str | None = Field(None, max_length=20)
    user_type: str = Field(default="user", pattern=r"^(system_admin|organization_admin|user|guest)$")


class AdminUserUpdate(BaseModel):
    """Schema for partial update of a user via admin portal."""

    roles: list[AllowedRole] | None = None
    is_active: bool | None = None
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=20)
    user_type: str | None = Field(None, pattern=r"^(system_admin|organization_admin|user|guest)$")


# ── List / Detail responses ──────────────────────────────────────────

class AdminUserListItem(BaseModel):
    """Single user in a paginated list."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    phone: str | None = None
    roles: list[str] = []
    user_type: str
    is_active: bool
    organization_id: UUID | None = None
    organization_name: str | None = None
    created_at: datetime


class AdminUserListResponse(BaseModel):
    """Paginated list of users."""

    users: list[AdminUserListItem]
    pagination: PaginationMeta


class AdminUserDetailResponse(BaseModel):
    """Full user detail with organization name."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    display_name: str | None = None
    phone: str | None = None
    roles: list[str] = []
    user_type: str
    is_active: bool
    organization_id: UUID | None = None
    organization_name: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
