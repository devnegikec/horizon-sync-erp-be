"""Public feature flag evaluation endpoint.

Accessible to any authenticated user (not admin-only).
GET /api/v1/feature-flags/evaluate/{feature_name}

Note: This endpoint uses a lightweight auth check that does NOT require
the user to belong to an organization. Feature flags are global and must
be evaluable immediately after signup/onboarding, before org context is set.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import decode_token
from app.database import get_db
from app.schemas.feature_flag import FeatureFlagEvaluation
from app.services.feature_flag_service import FeatureFlagService

router = APIRouter()

_security = HTTPBearer()


async def _require_any_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> str:
    """
    Minimal auth check: just verify the JWT is valid.
    Does NOT require organization membership — feature flags are global.
    """
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


@router.get("/evaluate/{feature_name}", response_model=FeatureFlagEvaluation)
async def evaluate_flag(
    feature_name: str,
    db: Session = Depends(get_db),
    _token: str = Depends(_require_any_authenticated_user),
) -> FeatureFlagEvaluation:
    """Evaluate a feature flag by name. Any authenticated user can call this."""
    service = FeatureFlagService(db)
    return service.evaluate(feature_name)
