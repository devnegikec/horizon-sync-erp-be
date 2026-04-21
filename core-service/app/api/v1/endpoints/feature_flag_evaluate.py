"""Public feature flag evaluation endpoint.

Accessible to any authenticated user (not admin-only).
GET /api/v1/feature-flags/evaluate/{feature_name}
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.feature_flag import FeatureFlagEvaluation
from app.services.feature_flag_service import FeatureFlagService

router = APIRouter()


@router.get("/evaluate/{feature_name}", response_model=FeatureFlagEvaluation)
async def evaluate_flag(
    feature_name: str,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_active_user),
) -> FeatureFlagEvaluation:
    """Evaluate a feature flag by name. Any authenticated user can call this."""
    service = FeatureFlagService(db)
    return service.evaluate(feature_name)
