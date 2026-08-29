"""Pick configuration endpoints (PR-02 / T-17, NFR-008).

Tenant-scoped WMS pick settings. ``GET /catalog`` powers the settings editor;
``GET`` returns effective values (defaults + overrides); ``PUT`` upserts
overrides with server-side validation; ``POST /reset`` clears overrides.

All routes require ``organization.update`` permission (same as Feature Flags).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.pick_config import catalog_entries
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.pick_settings import (
    PickConfigCatalogResponse,
    PickSettingsResponse,
    PickSettingsUpdate,
)
from app.services.pick_settings_service import PickSettingsService

router = APIRouter()


def _org_id(current_user: CurrentUser) -> str:
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no organization",
        )
    return current_user.organization_id


@router.get(
    "/catalog",
    response_model=PickConfigCatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="List pick config keys with types and defaults",
)
async def get_pick_config_catalog(
    current_user: CurrentUser = Depends(require_permission("organization.update")),
) -> PickConfigCatalogResponse:
    """Return the full catalog of pick.* keys for the settings editor."""
    return PickConfigCatalogResponse(config=catalog_entries())


@router.get(
    "",
    response_model=PickSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get effective pick settings for the current organization",
)
async def get_pick_settings(
    current_user: CurrentUser = Depends(require_permission("organization.update")),
    db: Session = Depends(get_db),
) -> PickSettingsResponse:
    """Return defaults merged with this organization's overrides."""
    org_id = _org_id(current_user)
    svc = PickSettingsService(db)
    return PickSettingsResponse(
        organization_id=org_id,
        settings=svc.get_settings(org_id),
    )


@router.put(
    "",
    response_model=PickSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Upsert pick settings overrides for the current organization",
)
async def update_pick_settings(
    body: PickSettingsUpdate,
    current_user: CurrentUser = Depends(require_permission("organization.update")),
    db: Session = Depends(get_db),
) -> PickSettingsResponse:
    """Validate and upsert one or more pick.* overrides."""
    org_id = _org_id(current_user)
    svc = PickSettingsService(db)
    try:
        settings = svc.update_settings(
            org_id, body.settings, updated_by=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e
    return PickSettingsResponse(organization_id=org_id, settings=settings)


@router.post(
    "/reset",
    response_model=PickSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset pick settings to defaults for the current organization",
)
async def reset_pick_settings(
    current_user: CurrentUser = Depends(require_permission("organization.update")),
    db: Session = Depends(get_db),
) -> PickSettingsResponse:
    """Delete all overrides so the organization falls back to defaults."""
    org_id = _org_id(current_user)
    svc = PickSettingsService(db)
    svc.reset_to_defaults(org_id)
    return PickSettingsResponse(
        organization_id=org_id,
        settings=svc.get_settings(org_id),
    )
