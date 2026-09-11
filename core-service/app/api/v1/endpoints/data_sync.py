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


class ReceiveAsnItemConfig(BaseModel):
    """A single item line for the 'receive_asn' feature."""

    item_id: UUID | None = Field(
        default=None, description="Item UUID (resolved by sku if omitted)"
    )
    sku: str | None = Field(
        default=None, description="Item SKU/code used to resolve the item"
    )
    batch: str = Field(
        default="", description="Base batch number; a sequence suffix is appended automatically"
    )
    quantity: int = Field(default=10, ge=1, le=5000)
    master_pack_size: int = Field(default=2, ge=1)


class ReceiveAsnOptions(BaseModel):
    """Options for the 'receive_asn' data-sync feature (Inbound Automation)."""

    mode: str = Field(
        default="items",
        description="'items' uses configured item lines; 'block_ids' receives existing blocks",
    )
    steps: list[str] = Field(
        default_factory=list,
        description=(
            "Inbound Automation steps to run, in dependency order. One or more of "
            "'qr_blocks', 'asn', 'receiving_slip', 'put_away'. Each later step "
            "depends on the previous. Empty defaults to qr_blocks+asn+receiving_slip."
        ),
    )
    qr_image: bool = Field(
        default=True, description="Whether to generate QR images for step 1 blocks"
    )
    items: list[ReceiveAsnItemConfig] = Field(default_factory=list)
    block_ids: list[str] = Field(default_factory=list)
    qr_type: str = Field(default="dynamic", description="'dynamic' or 'static'")
    asn_type: str = Field(
        default="purchase",
        description="'purchase' | 'stock_receipt' | 'internal_transfer'",
    )
    source_warehouse_id: UUID | None = Field(
        default=None, description="Source warehouse (required for internal_transfer)"
    )
    target_warehouse_id: UUID | None = Field(
        default=None, description="Target warehouse"
    )
    put_away_worker_ids: list[UUID] = Field(
        default_factory=list,
        description=(
            "Worker user IDs to distribute the put-away work across "
            "(step 'put_away'). Populated from the target warehouse's workers."
        ),
    )


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
    stock_boost_qty: int | None = Field(
        default=None,
        gt=0,
        description="Quantity to add to every item's stock level ('stock_boost' feature)",
    )
    receive_asn: ReceiveAsnOptions | None = Field(
        default=None,
        description="Options for the 'receive_asn' feature (create ASN + receiving slip from QR blocks)",
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
        stock_boost_qty=request.stock_boost_qty,
        receive_asn_options=(
            request.receive_asn.model_dump() if request.receive_asn else None
        ),
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
