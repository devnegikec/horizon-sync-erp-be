"""Internal feature flag listing for service-to-service calls.

The Identity Service needs to know which GLOBAL module feature flags are
disabled so it can filter module-specific permissions out of role and
permission responses (e.g. ``GET /roles?include_permissions=true``).

Protected by the shared ``X-Internal-Secret`` header (same mechanism as the
other ``/internal/*`` endpoints).
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constants import DEFAULT_SCOPE
from app.database import get_db
from app.dependencies import require_internal_service
from app.repositories.feature_flag_repository import FeatureFlagRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/internal/feature-flags",
    summary="List GLOBAL feature flags (internal service-to-service)",
    description=(
        "Returns every GLOBAL-scoped feature flag with its enabled/visible "
        "state. Consumed by the Identity Service to gate module-specific "
        "permissions in role and permission responses."
    ),
    tags=["Internal"],
)
async def list_global_feature_flags(
    db: Session = Depends(get_db),
    _internal: None = Depends(require_internal_service),
) -> dict:
    """Return all GLOBAL feature flags."""
    repo = FeatureFlagRepository(db)
    flags = repo.list_by_scope(DEFAULT_SCOPE)
    payload = [
        {
            "name": flag.name,
            "enabled": bool(flag.enabled),
            "visible": bool(flag.visible),
        }
        for flag in flags
    ]
    logger.info("Serving %d GLOBAL feature flags to an internal caller", len(payload))
    return {"flags": payload}
