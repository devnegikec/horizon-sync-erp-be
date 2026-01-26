"""Role related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.permission import PermissionResponse


class RoleBase(BaseModel):
    """Base role schema with common fields"""

    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=500)
    is_system: bool = Field(False)
    is_default: bool = Field(False)
    hierarchy_level: int = Field(0, ge=0)
    is_active: bool = Field(True)
    extra_data: dict | None = Field(default_factory=dict)


class RoleCreate(RoleBase):
    """Schema for creating a new role"""

    organization_id: UUID


class RoleUpdate(BaseModel):
    """Schema for updating a role"""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    hierarchy_level: int | None = Field(None, ge=0)
    is_active: bool | None = None
    extra_data: dict | None = None


class RoleResponse(RoleBase):
    """Schema for role response"""

    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime
    permissions: list[PermissionResponse] | None = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RoleListResponse(BaseModel):
    """Schema for paginated role list response"""

    data: list[RoleResponse]
    total: int
    skip: int
    limit: int


class RolePermissionBase(BaseModel):
    """Base role-permission schema"""

    role_id: UUID
    permission_id: UUID
    conditions: dict | None = Field(default_factory=dict)


class RolePermissionCreate(BaseModel):
    """Schema for creating role-permission mapping"""

    permission_id: UUID
    conditions: dict | None = Field(default_factory=dict)


class RolePermissionUpdate(BaseModel):
    """Schema for updating role-permission mapping"""

    conditions: dict | None = None


class RolePermissionResponse(BaseModel):
    """Schema for role-permission response"""

    id: UUID
    role_id: UUID
    permission_id: UUID
    conditions: dict

    model_config = ConfigDict(from_attributes=True)


class RolePermissionDetailResponse(BaseModel):
    """Schema for role-permission detail with permission info"""

    id: UUID
    role_id: UUID
    permission_id: UUID
    code: str
    name: str
    resource: str
    action: str
    module: str | None = None
    conditions: dict


class BulkAssignRolePermissionsRequest(BaseModel):
    """Schema for bulk role permission assignment"""

    permission_ids: list[UUID] = Field(..., min_items=1)
    mode: str = Field("replace", pattern="^(replace|add)$")


class RoleUserResponse(BaseModel):
    """Schema for user assigned to a role"""

    id: UUID
    user_id: UUID
    email: str
    first_name: str
    last_name: str
    is_primary: bool
    is_active: bool
    status: str
    joined_at: datetime | None = None


class RoleUsersListResponse(BaseModel):
    """Schema for paginated role users list response"""

    data: list[RoleUserResponse]
    total: int
    skip: int
    limit: int
