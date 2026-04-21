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


class FeatureFlagUpdate(BaseModel):
    name: str | None = Field(
        None, min_length=1, max_length=255, pattern=r"^[a-z0-9_]+$"
    )
    description: str | None = None
    enabled: bool | None = None


class FeatureFlagResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    enabled: bool
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
