"""Admin portal Pydantic schemas for identity-service"""

from uuid import UUID

from pydantic import BaseModel, EmailStr


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
