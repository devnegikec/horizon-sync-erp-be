"""Tenant feature flag management endpoints (Settings → Feature Flags).

Allows organization administrators to view effective flags for their tenant
(tenant override or inherited global) and upsert TENANT-scoped overrides.

GET  /api/v1/feature-flags/{feature_name}? No — the admin list/update lives here:
GET  /api/v1/feature-flags
PUT  /api/v1/feature-flags/{feature_name}
"""

import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.feature_flag import (
    FeatureFlagResponse,
    FeatureFlagTenantUpdate,
    TenantFeatureFlagListResponse,
)
from app.services.feature_flag_service import FeatureFlagService

router = APIRouter()

_FEATURE_NAME_RE = re.compile(r"^[a-z0-9_]+$")


def _validate_feature_name(feature_name: str) -> str:
    if not _FEATURE_NAME_RE.match(feature_name):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="feature_name must match ^[a-z0-9_]+$",
        )
    return feature_name


@router.get("", response_model=TenantFeatureFlagListResponse)
async def list_feature_flags(
    current_user: CurrentUser = Depends(require_permission("organization.update")),
    db: Session = Depends(get_db),
) -> TenantFeatureFlagListResponse:
    """List effective feature flags for the current user's organization."""
    if current_user.organization_id is None:
        return TenantFeatureFlagListResponse(flags=[])
    svc = FeatureFlagService(db)
    flags = svc.list_flags_for_org(current_user.organization_id)
    return TenantFeatureFlagListResponse(flags=flags)


@router.put("/{feature_name}", response_model=FeatureFlagResponse)
async def upsert_feature_flag(
    feature_name: str,
    body: FeatureFlagTenantUpdate,
    current_user: CurrentUser = Depends(require_permission("organization.update")),
    db: Session = Depends(get_db),
) -> FeatureFlagResponse:
    """Create or update a TENANT-scoped feature flag override."""
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no organization",
        )
    feature_name = _validate_feature_name(feature_name)
    svc = FeatureFlagService(db)
    return svc.upsert_tenant_flag(
        current_user.organization_id, feature_name, body
    )
