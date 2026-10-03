"""Feature flag schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FeatureFlagCreate(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=255, pattern=r"^[a-z0-9_]+$"
    )
    description: str | None = Field(None, max_length=1000)
    enabled: bool = Field(default=False)
    visible: bool = Field(default=True)


class FeatureFlagUpdate(BaseModel):
    name: str | None = Field(
        None, min_length=1, max_length=255, pattern=r"^[a-z0-9_]+$"
    )
    description: str | None = None
    enabled: bool | None = None
    visible: bool | None = None


class FeatureFlagResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    enabled: bool
    visible: bool
    scope: str
    tenant_id: UUID | None
    user_id: UUID | None
    rollout_percentage: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FeatureFlagListResponse(BaseModel):
    flags: list[FeatureFlagResponse]


class FeatureFlagEvaluation(BaseModel):
    feature_name: str
    enabled: bool
    visible: bool


class FeatureFlagTenantUpdate(BaseModel):
    """Upsert payload for a tenant-scoped feature flag override."""

    enabled: bool | None = None
    visible: bool | None = None
    description: str | None = Field(None, max_length=1000)


class TenantFeatureFlagResponse(BaseModel):
    """Effective view of a flag for a tenant (override or inherited global)."""

    name: str
    description: str | None
    enabled: bool
    visible: bool
    scope: str
    tenant_id: UUID | None
    inherited: bool


class TenantFeatureFlagListResponse(BaseModel):
    flags: list[TenantFeatureFlagResponse]


class FeatureFlagVisibility(BaseModel):
    feature_name: str
    enabled: bool
    visible: bool
