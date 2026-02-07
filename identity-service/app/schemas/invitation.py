"""Invitation related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class InvitationBase(BaseModel):
    """Base invitation schema with common fields"""

    email: EmailStr = Field(..., description="Email address to invite")
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    role_id: UUID | None = Field(None, description="Role to assign to the user")
    custom_permission_ids: list[UUID] | None = Field(
        default_factory=list,
        description="Custom permissions to assign (overrides role permissions)",
    )
    team_ids: list[UUID] | None = Field(
        default_factory=list, description="Teams to add user to"
    )
    message: str | None = Field(None, max_length=1000, description="Personal message")
    extra_data: dict | None = Field(default_factory=dict)


class InvitationCreate(InvitationBase):
    """Schema for creating a new invitation"""

    organization_id: UUID = Field(..., description="Organization to invite to")


class InvitationUpdate(BaseModel):
    """Schema for updating an invitation"""

    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    role_id: UUID | None = None
    team_ids: list[UUID] | None = None
    message: str | None = Field(None, max_length=1000)
    extra_data: dict | None = None


class InvitationResponse(BaseModel):
    """Schema for invitation response"""

    id: UUID
    organization_id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    role_id: UUID | None = None
    role_name: str | None = None
    custom_permission_ids: list[UUID] | None = None
    team_ids: list[UUID] | None = None
    invited_by_id: UUID | None = None
    invited_by_email: str | None = None
    status: str
    expires_at: datetime
    accepted_at: datetime | None = None
    message: str | None = None
    extra_data: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvitationListResponse(BaseModel):
    """Schema for paginated invitation list response"""

    data: list[InvitationResponse]
    total: int
    skip: int
    limit: int


class InvitationAcceptRequest(BaseModel):
    """Schema for accepting an invitation"""

    token: str = Field(..., description="Invitation token")
    password: str = Field(..., min_length=8, max_length=100, description="New password")
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)


class InvitationAcceptResponse(BaseModel):
    """Schema for invitation acceptance response"""

    message: str
    user_id: UUID
    organization_id: UUID
    email: str


class ResendInvitationRequest(BaseModel):
    """Schema for resending an invitation"""

    invitation_id: UUID


class BulkInvitationCreate(BaseModel):
    """Schema for bulk invitation creation"""

    organization_id: UUID
    invitations: list[InvitationBase] = Field(..., min_length=1, max_length=50)


class BulkInvitationResponse(BaseModel):
    """Schema for bulk invitation response"""

    sent_count: int
    failed_count: int
    results: list[dict]
