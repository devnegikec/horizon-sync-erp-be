"""User related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema with common fields"""

    email: EmailStr
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    phone: str | None = Field(None, max_length=20)


class UserCreate(UserBase):
    """Schema for creating a new user"""

    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for partial user update"""

    email: EmailStr | None = None
    first_name: str | None = Field(None, min_length=2, max_length=100)
    last_name: str | None = Field(None, min_length=2, max_length=100)
    phone: str | None = Field(None, max_length=20)
    user_type: str | None = Field(
        None, pattern="^(system_admin|organization_admin|user|guest)$"
    )
    status: str | None = Field(None, pattern="^(active|inactive|suspended|pending)$")


class UserResponse(UserBase):
    """Schema for user response"""

    id: UUID
    display_name: str | None = None
    user_type: str
    status: str
    email_verified: bool
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListItem(BaseModel):
    """Schema for user in list response"""

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    display_name: str | None = None
    user_type: str
    status: str
    email_verified: bool
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class UserListResponse(BaseModel):
    """Schema for paginated user list response"""

    users: list[UserListItem]
    pagination: PaginationMeta
