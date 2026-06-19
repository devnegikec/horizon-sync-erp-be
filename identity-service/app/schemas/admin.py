"""Admin portal Pydantic schemas for identity-service"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class AdminProfileResponse(BaseModel):
    """Response schema for GET /identity/admin/me"""

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    display_name: str | None = None
    user_type: str
    organization_id: str | None = None
    permissions: list[str] = []


class CreateWarehouseWorkerRequest(BaseModel):
    """Schema for creating a warehouse worker user (admin only)

    Workers log in exclusively via QR code scan — they do not use
    email/password auth. If email is not provided, one is auto-generated
    from the QR code value.
    """

    email: EmailStr | None = None
    first_name: str
    last_name: str
    phone: str | None = None
    qr_code: str
    organization_id: UUID
    warehouse_ids: list[UUID] | None = None
    warehouse_role: str | None = "operator"  # supervisor, manager, operator, coordinator


class WarehouseWorkerResponse(BaseModel):
    """Response schema for created warehouse worker"""

    id: UUID
    email: str
    first_name: str
    last_name: str
    display_name: str | None = None
    phone: str | None = None
    user_type: str
    status: str
    is_active: bool
    qr_code: str | None = None
    organization_id: str | None = None
    created_at: datetime | None = None
    last_login_at: datetime | None = None
    warehouse_assignments: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class WarehouseWorkerUpdateRequest(BaseModel):
    """Schema for updating a warehouse worker"""

    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    qr_code: str | None = None
    is_active: bool | None = None


class WarehouseWorkerListResponse(BaseModel):
    """Paginated list of warehouse workers"""

    workers: list[WarehouseWorkerResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
