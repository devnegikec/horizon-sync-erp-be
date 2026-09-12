"""Public feature flag evaluation endpoint.

Accessible to any authenticated user (not admin-only).
GET /api/v1/feature-flags/evaluate/{feature_name}

Tenant-aware: when the caller belongs to an organization, a TENANT-scoped
override is evaluated first (falling back to the GLOBAL value). Callers
without an organization (pre-onboarding) get the GLOBAL value only.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.dependencies import _get_user_org_and_permissions
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


async def _resolve_org_tolerantly(token: str) -> UUID | None:
    """Resolve the caller's org id; return None on any error (no org yet)."""
    try:
        org_id, _permissions = await _get_user_org_and_permissions(token)
        return org_id
    except Exception:
        return None


@router.get("/evaluate/{feature_name}", response_model=FeatureFlagEvaluation)
async def evaluate_flag(
    feature_name: str,
    db: Session = Depends(get_db),
    token: str = Depends(_require_any_authenticated_user),
) -> FeatureFlagEvaluation:
    """Evaluate a feature flag for the current user (tenant-aware)."""
    service = FeatureFlagService(db)
    org_id = await _resolve_org_tolerantly(token)
    if org_id is not None:
        return service.evaluate_for_org(feature_name, org_id)
    return service.evaluate(feature_name)
