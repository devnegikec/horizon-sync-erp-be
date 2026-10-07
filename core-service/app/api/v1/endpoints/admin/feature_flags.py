"""Feature Flag Management API Endpoints for System Administrators.

POST   /admin/feature-flags                                  — create flag (201)
GET    /admin/feature-flags?scope=&organization_id=          — list flags (filterable)
GET    /admin/feature-flags/evaluate/{feature_name}          — evaluate flag (200)
GET    /admin/feature-flags/{flag_id}                        — get by ID (200)
PATCH  /admin/feature-flags/{flag_id}                        — update flag (200)
DELETE /admin/feature-flags/{flag_id}                        — delete flag (204)

Org-wise (TENANT-scoped) control:
GET    /admin/feature-flags/tenants/{organization_id}                    — list tenant flags
PUT    /admin/feature-flags/tenants/{organization_id}/{feature_name}     — enable/disable for org
DELETE /admin/feature-flags/tenants/{organization_id}/{feature_name}     — remove org override
"""

from uuid import UUID

import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_admin
from app.schemas.feature_flag import (
    FeatureFlagCreate,
    FeatureFlagEvaluation,
    FeatureFlagListResponse,
    FeatureFlagResponse,
    FeatureFlagTenantUpdate,
    FeatureFlagUpdate,
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


@router.post("", response_model=FeatureFlagResponse, status_code=status.HTTP_201_CREATED)
async def create_flag(
    body: FeatureFlagCreate,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> FeatureFlagResponse:
    """Create a new GLOBAL-scoped feature flag."""
    service = FeatureFlagService(db)
    return service.create_flag(body)


@router.get("", response_model=FeatureFlagListResponse)
async def list_flags(
    scope: str | None = Query(
        None, description="Filter by scope: GLOBAL or TENANT"
    ),
    organization_id: UUID | None = Query(
        None, description="Filter TENANT flags by organization ID"
    ),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> FeatureFlagListResponse:
    """List feature flags, optionally filtered by scope and organization."""
    service = FeatureFlagService(db)
    if scope is not None:
        scope = scope.upper()
    return service.list_flags(scope=scope, organization_id=organization_id)


# NOTE: evaluate route is placed BEFORE /{flag_id} to avoid path conflicts
@router.get("/evaluate/{feature_name}", response_model=FeatureFlagEvaluation)
async def evaluate_flag(
    feature_name: str,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> FeatureFlagEvaluation:
    """Evaluate a feature flag by name. Returns enabled=false for missing flags."""
    service = FeatureFlagService(db)
    return service.evaluate(feature_name)


@router.get(
    "/tenants/{organization_id}",
    response_model=FeatureFlagListResponse,
)
async def list_tenant_flags(
    organization_id: UUID,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> FeatureFlagListResponse:
    """List the TENANT-scoped feature flags for a specific organization."""
    service = FeatureFlagService(db)
    return FeatureFlagListResponse(flags=service.list_tenant_flags(organization_id))


@router.put(
    "/tenants/{organization_id}/{feature_name}",
    response_model=FeatureFlagResponse,
)
async def upsert_tenant_flag(
    organization_id: UUID,
    feature_name: str,
    body: FeatureFlagTenantUpdate,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> FeatureFlagResponse:
    """Enable/disable (upsert) a TENANT-scoped flag for a specific organization."""
    feature_name = _validate_feature_name(feature_name)
    service = FeatureFlagService(db)
    return service.upsert_tenant_flag(organization_id, feature_name, body)


@router.delete(
    "/tenants/{organization_id}/{feature_name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_tenant_flag(
    organization_id: UUID,
    feature_name: str,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> None:
    """Delete a TENANT-scoped flag override for a specific organization."""
    feature_name = _validate_feature_name(feature_name)
    service = FeatureFlagService(db)
    service.delete_tenant_flag(organization_id, feature_name)


@router.get("/{flag_id}", response_model=FeatureFlagResponse)
async def get_flag(
    flag_id: UUID,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> FeatureFlagResponse:
    """Get a feature flag by ID."""
    service = FeatureFlagService(db)
    return service.get_flag(flag_id)


@router.patch("/{flag_id}", response_model=FeatureFlagResponse)
async def update_flag(
    flag_id: UUID,
    body: FeatureFlagUpdate,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> FeatureFlagResponse:
    """Update a feature flag (partial update)."""
    service = FeatureFlagService(db)
    return service.update_flag(flag_id, body)


@router.delete("/{flag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flag(
    flag_id: UUID,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> None:
    """Delete a feature flag."""
    service = FeatureFlagService(db)
    service.delete_flag(flag_id)

