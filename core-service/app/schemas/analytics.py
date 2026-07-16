"""Pydantic schemas for Analytics module"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel

# ── QR Scan Event ─────────────────────────────────────────────────────────────


class QRScanEventIngest(BaseModel):
    """Payload sent by the QR landing page on each scan"""

    serial_number: str
    product_item_id: UUID | None = None
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


class QRScanEventResponse(BaseModel):
    id: UUID
    organization_id: UUID
    serial_number: str | None
    product_item_id: UUID | None
    scan_timestamp: datetime
    device_type: str | None
    os: str | None
    browser: str | None
    city: str | None
    state: str | None
    country: str | None

    model_config = {"from_attributes": True}


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


# ── CTA Breakdown ─────────────────────────────────────────────────────────────


class CTABreakdownItem(BaseModel):
    cta_action: str | None
    count: int


class CTABreakdownResponse(BaseModel):
    breakdown: list[CTABreakdownItem]
    total_scans_with_cta: int


# ── Geo Heatmap ───────────────────────────────────────────────────────────────


class GeoHeatmapItem(BaseModel):
    city: str | None
    state: str | None
    country: str | None
    latitude: float | None
    longitude: float | None
    count: int


# ── Device Timeline ───────────────────────────────────────────────────────────


class DeviceTimelineItem(BaseModel):
    date: str
    mobile: int = 0
    desktop: int = 0
    tablet: int = 0
    unknown: int = 0


# ── Interaction Funnel ────────────────────────────────────────────────────────


class InteractionTypeCount(BaseModel):
    interaction_type: str | None
    count: int


class InteractionFunnelResponse(BaseModel):
    total_scans: int
    scans_with_cta: int
    scans_with_interactions: int
    total_interactions: int
    conversion_rate: float
    top_interaction_types: list[InteractionTypeCount]
