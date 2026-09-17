"""Analytics module endpoints"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.constants import ANALYTICS_MODULE_ENABLED
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, require_feature_flag
from app.schemas.analytics import (
    CTABreakdownResponse,
    CTAConfigCreate,
    CTAConfigResponse,
    CTAConfigUpdate,
    DeviceTimelineResponse,
    GeoHeatmapResponse,
    InteractionFunnelResponse,
    MetaCampaignCreate,
    MetaCampaignListResponse,
    MetaCampaignResponse,
    QRScanAnalyticsResponse,
    QRScanEventIngest,
    QRScanEventResponse,
    ScanInteractionIngest,
    ScanInteractionResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(
    dependencies=[Depends(require_feature_flag(ANALYTICS_MODULE_ENABLED))]
)


def get_service(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


# ── QR Scan Event Ingestion ───────────────────────────────────────────────────


@router.post(
    "/scans/ingest",
    response_model=QRScanEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a QR scan event (public — called by QR landing page)",
)
async def ingest_scan(
    data: QRScanEventIngest,
    request: Request,
    organization_id: UUID = Query(
        ..., description="Organization that owns the QR code"
    ),
    service: AnalyticsService = Depends(get_service),
):
    """No auth required — called by the consumer-facing QR landing page."""
    return await service.ingest_scan(data, organization_id, dict(request.headers))


@router.post(
    "/scans/{scan_id}/interactions",
    response_model=ScanInteractionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a post-scan interaction (public)",
)
def record_interaction(
    scan_id: UUID,
    data: ScanInteractionIngest,
    organization_id: UUID = Query(
        ..., description="Organization that owns the scan event"
    ),
    service: AnalyticsService = Depends(get_service),
):
    interaction = service.record_interaction(scan_id, data, organization_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="Scan event not found")
    return interaction


@router.get(
    "/scans/{scan_id}/interactions",
    response_model=list[ScanInteractionResponse],
    summary="List interactions for a scan event",
)
def list_interactions(
    scan_id: UUID,
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    return service.list_interactions(scan_id, current_user.organization_id)


@router.get(
    "/scans",
    summary="List QR scan events",
)
def list_scan_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    serial_number: str | None = Query(None),
    product_item_id: UUID | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.list_scan_events(
        org_id, page, page_size, serial_number, product_item_id, date_from, date_to
    )


@router.get(
    "/scans/summary",
    response_model=QRScanAnalyticsResponse,
    summary="Get QR scan analytics summary",
)
def get_scan_analytics(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    serial_number: str | None = Query(None, description="Filter to a single serial"),
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.get_scan_analytics(org_id, date_from, date_to, serial_number)


# ── Enhanced Analytics ────────────────────────────────────────────────────────


@router.get(
    "/scans/interaction-funnel",
    response_model=InteractionFunnelResponse,
    summary="Get interaction funnel (scans → unique products → CTA clicks)",
)
def get_interaction_funnel(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.get_interaction_funnel(org_id, date_from, date_to)


@router.get(
    "/scans/cta-breakdown",
    response_model=CTABreakdownResponse,
    summary="Get CTA button click breakdown",
)
def get_cta_breakdown(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.get_cta_breakdown(org_id, date_from, date_to)


@router.get(
    "/scans/geo-heatmap",
    response_model=GeoHeatmapResponse,
    summary="Get geographic heatmap data for scans",
)
def get_geo_heatmap(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.get_geo_heatmap(org_id, date_from, date_to, limit)


@router.get(
    "/scans/device-timeline",
    response_model=DeviceTimelineResponse,
    summary="Get scan counts over time grouped by device type",
)
def get_device_timeline(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.get_device_timeline(org_id, date_from, date_to)


# ── CTA Configuration ──────────────────────────────────────────────────────────


@router.post(
    "/products/{product_id}/ctas",
    response_model=CTAConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product CTA configuration",
)
def create_cta_config(
    product_id: UUID,
    data: CTAConfigCreate,
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    config = service.create_cta_config(data, current_user.organization_id, product_id)
    if config is None:
        raise HTTPException(status_code=404, detail="QR product not found")
    return config


@router.get(
    "/products/{product_id}/ctas",
    response_model=list[CTAConfigResponse],
    summary="List CTA configurations for a product",
)
def list_cta_configs(
    product_id: UUID,
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    return service.list_cta_configs(current_user.organization_id, product_id)


@router.get(
    "/products/{product_id}/ctas/{config_id}",
    response_model=CTAConfigResponse,
    summary="Get a product CTA configuration",
)
def get_cta_config(
    product_id: UUID,
    config_id: UUID,
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    config = service.get_cta_config(config_id, current_user.organization_id)
    if config is None or config.product_id != product_id:
        raise HTTPException(status_code=404, detail="CTA configuration not found")
    return config


@router.put(
    "/products/{product_id}/ctas/{config_id}",
    response_model=CTAConfigResponse,
    summary="Update a product CTA configuration",
)
def update_cta_config(
    product_id: UUID,
    config_id: UUID,
    data: CTAConfigUpdate,
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    config = service.update_cta_config(
        config_id,
        data,
        current_user.organization_id,
        product_id,
    )
    if config is None:
        raise HTTPException(status_code=404, detail="CTA configuration not found")
    return config


@router.delete(
    "/products/{product_id}/ctas/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product CTA configuration",
)
def delete_cta_config(
    product_id: UUID,
    config_id: UUID,
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    deleted = service.delete_cta_config(
        config_id,
        current_user.organization_id,
        product_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="CTA configuration not found")


# ── Meta Campaign Analytics ───────────────────────────────────────────────────


@router.post(
    "/meta-campaigns",
    response_model=MetaCampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a Meta Ads campaign snapshot",
)
def record_meta_snapshot(
    data: MetaCampaignCreate,
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.record_meta_snapshot(data, org_id)


@router.get(
    "/meta-campaigns",
    response_model=MetaCampaignListResponse,
    summary="List Meta campaign snapshots",
)
def list_meta_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    campaign_id: str | None = Query(None, description="Filter by Meta campaign ID"),
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.list_meta_campaigns(org_id, page, page_size, campaign_id)


@router.get(
    "/meta-campaigns/{mc_id}",
    response_model=MetaCampaignResponse,
    summary="Get a single Meta campaign snapshot",
)
def get_meta_campaign(
    mc_id: UUID,
    service: AnalyticsService = Depends(get_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    org_id = current_user.organization_id
    mc = service.get_meta_campaign(mc_id, org_id)
    if not mc:
        raise HTTPException(status_code=404, detail="Meta campaign record not found")
    return mc
