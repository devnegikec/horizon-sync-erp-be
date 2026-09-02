"""On-demand data sync endpoints (Settings → Data Sync).

Allows organization administrators to re-seed individual default master-data
categories on demand. Every seed routine is idempotent, so syncing a category
that is already populated simply skips existing records.

GET  /api/v1/data-sync/features
POST /api/v1/data-sync/sync
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.services.organization_onboarding_service import (
    SYNCABLE_FEATURE_KEYS,
    SYNCABLE_FEATURES,
    OrganizationOnboardingService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class FeatureCatalogItem(BaseModel):
    """A single syncable data category."""

    key: str
    label: str
    description: str


class FeatureCatalogResponse(BaseModel):
    """Response for the syncable feature catalog."""

    features: list[FeatureCatalogItem]


class DataSyncRequest(BaseModel):
    """Request body for on-demand data sync."""

    features: list[str] = Field(
        ...,
        min_length=1,
        description="List of feature keys to seed (see GET /data-sync/features)",
    )
    base_currency: str = Field(
        default="USD",
        max_length=3,
        description="ISO 4217 currency code used for currency/chart-of-accounts seeding",
    )
    warehouse_id: UUID | None = Field(
        default=None,
        description="Target warehouse for the 'stock' feature",
    )


class DataSyncResponse(BaseModel):
    """Response body for on-demand data sync."""

    success: bool
    organization_id: str
    message: str
    summary: dict


@router.get(
    "/features",
    response_model=FeatureCatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="List syncable data categories",
    tags=["Data Sync"],
)
async def list_syncable_features(
    current_user: CurrentUser = Depends(require_permission("organization.update")),
) -> FeatureCatalogResponse:
    """Return the catalog of on-demand seedable data categories."""
    return FeatureCatalogResponse(
        features=[FeatureCatalogItem(**feature) for feature in SYNCABLE_FEATURES]
    )


@router.post(
    "/sync",
    response_model=DataSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Seed selected data categories on demand",
    tags=["Data Sync"],
)
async def sync_data_features(
    request: DataSyncRequest,
    current_user: CurrentUser = Depends(require_permission("organization.update")),
    db: Session = Depends(get_db),
) -> DataSyncResponse:
    """Seed the requested default data categories for the current user's org.

    All seed routines are idempotent — re-syncing a category skips records
    that already exist and only creates missing ones.
    """
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no organization",
        )

    features = list(dict.fromkeys(request.features))  # de-duplicate, keep order
    unknown = [key for key in features if key not in SYNCABLE_FEATURE_KEYS]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown feature keys: {', '.join(unknown)}",
        )

    svc = OrganizationOnboardingService(db)
    summary = svc.sync_features(
        organization_id=current_user.organization_id,
        features=features,
        created_by=str(current_user.id),
        base_currency=request.base_currency.strip().upper() or "USD",
        warehouse_id=request.warehouse_id,
    )

    logger.info(
        "Data sync requested",
        extra={
            "organization_id": str(current_user.organization_id),
            "features": features,
            "event": "data_sync_requested",
        },
    )

    return DataSyncResponse(
        success=True,
        organization_id=str(current_user.organization_id),
        message=f"Seeded {len(features)} data categor{'y' if len(features) == 1 else 'ies'}",
        summary=summary,
    )
