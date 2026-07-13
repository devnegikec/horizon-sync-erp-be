"""Pydantic schemas for Analytics module"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel

# ── QR Scan Event ─────────────────────────────────────────────────────────────


class QRScanEventIngest(BaseModel):
    """Payload sent by the QR landing page on each scan.

    Fields marked with * are auto-enriched server-side from HTTP headers
    or external lookups — the client does not need to send them.
    """

    serial_number: str
    product_item_id: UUID | None = None
    # ── Client-provided (optional) ──────────────────────────────────────
    device_type: str | None = None
    os: str | None = None
    browser: str | None = None
    ip_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    extra_data: dict[str, Any] | None = None
    # ── Phase 2: CTA & QR type ──────────────────────────────────────────
    qr_type: str | None = None
    cta_action: str | None = None


class QRScanEventResponse(BaseModel):
    id: UUID
    organization_id: UUID
    serial_number: str | None
    product_item_id: UUID | None
    scan_timestamp: datetime
    device_type: str | None
    os: str | None
    browser: str | None
    ip_address: str | None
    latitude: float | None
    longitude: float | None
    city: str | None
    state: str | None
    country: str | None
    # ── Phase 2 fields ──────────────────────────────────────────────────
    user_agent_raw: str | None = None
    user_agent_parsed: dict[str, Any] | None = None
    qr_type: str | None = None
    cta_action: str | None = None
    referrer_url: str | None = None
    language: str | None = None

    model_config = {"from_attributes": True}


# ── QR Scan Interactions ──────────────────────────────────────────────────────


class ScanInteractionIngest(BaseModel):
    """Payload: record a post-scan user interaction.

    Called by the QR landing page whenever the user performs an action
    after scanning: clicking a CTA button, filling a form, watching a
    video, sharing the page, calling support, etc.
    """

    interaction_type: str
    interaction_target: str | None = None
    interaction_data: dict[str, Any] | None = None


class ScanInteractionResponse(BaseModel):
    id: UUID
    scan_event_id: UUID
    interaction_type: str
    interaction_target: str | None
    interaction_data: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Phase 4: Enhanced Analytics ───────────────────────────────────────────────


class CTABreakdownItem(BaseModel):
    cta_action: str
    count: int


class CTABreakdownResponse(BaseModel):
    breakdown: list[CTABreakdownItem]
    total_scans_with_cta: int


class GeoHeatmapItem(BaseModel):
    city: str | None
    state: str | None = None
    country: str | None = None
    latitude: float
    longitude: float
    count: int


class DeviceTimelineItem(BaseModel):
    date: str
    mobile: int
    desktop: int
    tablet: int
    unknown: int


class InteractionFunnelResponse(BaseModel):
    total_scans: int
    scans_with_cta: int
    scans_with_interactions: int
    total_interactions: int
    conversion_rate: float
    top_interaction_types: list[dict[str, Any]]


# ── QR Scan Analytics ─────────────────────────────────────────────────────────


class ScanCountByDate(BaseModel):
    date: str
    count: int


class ScanCountByGeo(BaseModel):
    country: str | None
    state: str | None = None
    city: str | None = None
    count: int


class ScanCountByDevice(BaseModel):
    device_type: str | None
    count: int


class QRScanAnalyticsResponse(BaseModel):
    total_scans: int
    unique_serials: int
    by_date: list[ScanCountByDate]
    by_country: list[ScanCountByGeo]
    by_device: list[ScanCountByDevice]


# ── Meta Campaigns ────────────────────────────────────────────────────────────


class MetaCampaignCreate(BaseModel):
    campaign_id: str | None = None
    campaign_name: str | None = None
    impressions: int | None = None
    clicks: int | None = None
    spend: Decimal | None = None
    reach: int | None = None
    extra_data: dict[str, Any] | None = None


class MetaCampaignResponse(BaseModel):
    id: UUID
    organization_id: UUID
    campaign_id: str | None
    campaign_name: str | None
    impressions: int | None
    clicks: int | None
    spend: Decimal | None
    reach: int | None
    fetched_at: datetime

    model_config = {"from_attributes": True}


class MetaCampaignListResponse(BaseModel):
    campaigns: list[MetaCampaignResponse]
    pagination: dict[str, Any]
