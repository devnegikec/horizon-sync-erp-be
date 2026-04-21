"""Feature Flag Management API Endpoints for System Administrators.

POST   /admin/feature-flags                        — create flag (201)
GET    /admin/feature-flags                        — list all flags (200)
GET    /admin/feature-flags/evaluate/{feature_name} — evaluate flag (200)
GET    /admin/feature-flags/{flag_id}              — get by ID (200)
PATCH  /admin/feature-flags/{flag_id}              — update flag (200)
DELETE /admin/feature-flags/{flag_id}              — delete flag (204)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_admin
from app.schemas.feature_flag import (
    FeatureFlagCreate,
    FeatureFlagEvaluation,
    FeatureFlagListResponse,
    FeatureFlagResponse,
    FeatureFlagUpdate,
)
from app.services.feature_flag_service import FeatureFlagService

router = APIRouter()


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
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> FeatureFlagListResponse:
    """List all feature flags."""
    service = FeatureFlagService(db)
    return service.list_flags()


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
