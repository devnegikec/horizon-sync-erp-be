"""User related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Base user schema with common fields"""

    email: EmailStr
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    phone: str | None = Field(None, max_length=20)


class UserCreate(UserBase):
    """Schema for creating a new user"""

    password: str = Field(..., min_length=8)
    organization_id: str | None = Field(
        None, description="Organization to assign user to"
    )
    user_type: str | None = Field(
        None,
        pattern="^(system_admin|organization_admin|user|guest)$",
        description="User type; defaults to 'user' if omitted",
    )
    system_admin_role_ids: list[str] | None = Field(
        None,
        description="Explicit role IDs to assign instead of the default role lookup",
    )


class UserUpdate(BaseModel):
    """Schema for partial user update (admin)"""

    email: EmailStr | None = None
    first_name: str | None = Field(None, min_length=2, max_length=100)
    last_name: str | None = Field(None, min_length=2, max_length=100)
    phone: str | None = Field(None, max_length=20)
    user_type: str | None = Field(
        None, pattern="^(system_admin|organization_admin|user|guest)$"
    )
    status: str | None = Field(None, pattern="^(active|inactive|suspended|pending)$")
    is_active: bool | None = None


class UserSelfUpdate(BaseModel):
    """Schema for self-service profile update (logged-in user updates own info)"""

    first_name: str | None = Field(None, min_length=2, max_length=100)
    last_name: str | None = Field(None, min_length=2, max_length=100)
    display_name: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=20)
    preferences: dict | None = None
    extra_data: dict | None = None
    timezone: str | None = Field(None, max_length=50)
    language: str | None = Field(None, max_length=10)


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


class UserProfileResponse(UserBase):
    """Schema for user profile (self-service) including preferences, extra_data, timezone"""

    id: UUID
    display_name: str | None = None
    user_type: str
    status: str
    email_verified: bool
    preferences: dict | None = None
    timezone: str | None = "UTC"
    language: str | None = "en"
    extra_data: dict | None = None
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
    # Org-level role names assigned to this user (e.g. ["Sales Agent", "Viewer"])
    roles: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class UserStatusCounts(BaseModel):
    """Counts of users by status and MFA for the list scope"""

    active: int = 0
    inactive: int = 0
    suspended: int = 0
    pending: int = 0
    mfa_enabled: int = 0


class UserRolesUpdate(BaseModel):
    """Schema for updating a user's organization roles"""

    organization_id: UUID
    role_ids: list[UUID] = Field(default_factory=list)
    custom_permission_ids: list[UUID] = Field(default_factory=list)

    @field_validator("role_ids", "custom_permission_ids", mode="before")
    @classmethod
    def coerce_role_ids(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        raise ValueError("must be a list of UUIDs")


class UserRolesResponse(BaseModel):
    """Schema for user roles update response"""

    user_id: UUID
    organization_id: UUID
    roles: list[str]


class UserListResponse(BaseModel):
    """Schema for paginated user list response"""

    users: list[UserListItem]
    pagination: PaginationMeta
    status_counts: UserStatusCounts
