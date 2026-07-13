"""Analytics module endpoints"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.constants import ANALYTICS_MODULE_ENABLED
from app.database import get_db
from app.dependencies import get_current_user, require_feature_flag
from app.schemas.analytics import (
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
    """No auth required — called by the consumer-facing QR landing page.

    Auto-enriches the scan with:
    - User-Agent parsing (browser, OS, device type)
    - Server-side IP geolocation fallback
    - Referrer URL and language from request headers
    """
    headers = dict(request.headers)
    return await service.ingest_scan(data, organization_id, headers)


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
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
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
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.get_scan_analytics(org_id, date_from, date_to, serial_number)


# ── Post-Scan Interactions ────────────────────────────────────────────────────


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
        ..., description="Organization that owns the QR code"
    ),
    service: AnalyticsService = Depends(get_service),
):
    """No auth required — called by the QR landing page when user clicks
    a CTA button, fills a form, calls support, watches a video, or shares.

    interaction_type examples: click, page_view, form_submit, call, share,
    download, video_play, video_complete
    """
    return service.record_interaction(scan_id, data, organization_id)


@router.get(
    "/scans/{scan_id}/interactions",
    summary="List all interactions for a scan event (authenticated)",
)
def list_interactions(
    scan_id: UUID,
    service: AnalyticsService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.list_interactions(scan_id, org_id)


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
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
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
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.list_meta_campaigns(org_id, page, page_size, campaign_id)


@router.get(
    "/meta-campaigns/{mc_id}",
    response_model=MetaCampaignResponse,
    summary="Get a single Meta campaign snapshot",
)
def get_meta_campaign(
    mc_id: UUID,
    service: AnalyticsService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    mc = service.get_meta_campaign(mc_id, org_id)
    if not mc:
        raise HTTPException(status_code=404, detail="Meta campaign record not found")
    return mc
