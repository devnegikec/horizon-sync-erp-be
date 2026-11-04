"""User related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.services.avatar_storage import (
    AVATAR_DATA_URL_PATTERN,
    max_base64_length,
)

# ``users.avatar_url`` is a varchar(500), so anything persisted there must fit.
STORED_AVATAR_URL_MAX_LENGTH = 500
# Inline uploads arrive base64-encoded; allow the largest supported image plus
# the ``data:image/...;base64,`` prefix.
MAX_AVATAR_FIELD_LENGTH = max_base64_length() + 100


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
    # Either an absolute http(s) URL of an already-hosted image, or an inline
    # ``data:image/...;base64,...`` payload from the browser. Inline payloads are
    # persisted by ``PATCH /users/me`` and replaced with a served URL. Prefer
    # ``POST /users/me/avatar`` (multipart), which avoids base64 inflation.
    avatar_url: str | None = Field(None, max_length=MAX_AVATAR_FIELD_LENGTH)
    preferences: dict | None = None
    extra_data: dict | None = None
    timezone: str | None = Field(None, max_length=50)
    language: str | None = Field(None, max_length=10)

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, value: str | None) -> str | None:
        """Accept an absolute http(s) URL or a base64 image data URL."""
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if value.lower().startswith("data:"):
            # The endpoint decodes and stores this payload, so only the format
            # needs checking here.
            if not AVATAR_DATA_URL_PATTERN.match(value):
                raise ValueError(
                    "avatar_url data URL must be a base64 PNG, JPEG or WebP image"
                )
            return value
        if not value.lower().startswith(("http://", "https://")):
            raise ValueError("avatar_url must be an absolute http(s) URL")
        if len(value) > STORED_AVATAR_URL_MAX_LENGTH:
            raise ValueError(
                f"avatar_url must be at most {STORED_AVATAR_URL_MAX_LENGTH} "
                "characters; upload the file with POST /users/me/avatar instead"
            )
        return value


class UserResponse(UserBase):
    """Schema for user response"""

    id: UUID
    display_name: str | None = None
    avatar_url: str | None = None
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
    avatar_url: str | None = None
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
