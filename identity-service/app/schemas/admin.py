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
    """Schema for creating a warehouse worker user.

    Workers log in via QR code scan. Supports both the new compact format
    and the legacy WMS worker format with login_username/employee_id/password.
    """

    first_name: str
    last_name: str
    email: EmailStr | None = None
    phone: str | None = None

    # QR code — auto-generated from employee_id if not provided
    qr_code: str | None = None

    # Organization — required, pass from Zustand state
    organization_id: UUID

    # Warehouse assignment
    warehouse_id: UUID | None = None  # legacy single-warehouse format
    warehouse_ids: list[UUID] | None = None  # multi-warehouse format
    warehouse_role: str | None = "operator"

    # Legacy WMS worker fields (stored in extra_data)
    login_username: str | None = None
    employee_id: str | None = None
    password: str | None = None

    # Role/status
    role: str | None = None
    status: str | None = None


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
