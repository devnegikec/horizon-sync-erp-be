"""Permission related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PermissionBase(BaseModel):
    """Base permission schema with common fields"""

    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)
    module: str | None = Field(None, max_length=50)
    category: str | None = Field(None, max_length=50)
    is_active: bool = Field(True)
    extra_data: dict | None = Field(default_factory=dict)


class PermissionCreate(PermissionBase):
    """Schema for creating a new permission"""

    pass


class PermissionUpdate(BaseModel):
    """Schema for updating a permission"""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_active: bool | None = None
    extra_data: dict | None = None


class PermissionResponse(PermissionBase):
    """Schema for permission response"""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PermissionListResponse(BaseModel):
    """Schema for paginated permission list response"""

    data: list[PermissionResponse]
    total: int
    skip: int
    limit: int


class BulkAssignPermissionsRequest(BaseModel):
    """Schema for bulk permission assignment"""

    permission_ids: list[UUID] = Field(..., min_items=1)
    mode: str = Field("replace", pattern="^(replace|add)$")
