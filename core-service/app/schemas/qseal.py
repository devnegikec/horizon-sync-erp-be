"""Pydantic schemas for QSeal module"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ── Parent QSeal ──────────────────────────────────────────────────────────────


class QSealParentCreate(BaseModel):
    name: str = Field(
        ..., max_length=20, description="Label for this parent node, e.g. 'Pallet'"
    )
    qseal_type: str = Field(
        ..., max_length=25, description="e.g. shipper, pallet, container"
    )
    capacity: int = Field(
        ..., gt=0, description="Max number of child QSeals this node can hold"
    )
    app_cascade_map: bool = False
    extra_data: dict[str, Any] | None = None


class QSealParentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    qseal_type: str | None
    name: str | None
    capacity: int | None
    serial_number: str | None
    qseal_code_link: str | None
    app_cascade_map: bool
    parent_id: UUID | None
    parent_app_id: UUID | None
    children_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class QSealParentListResponse(BaseModel):
    nodes: list[QSealParentResponse]
    pagination: dict[str, Any]


# ── Child QSeal ───────────────────────────────────────────────────────────────


class QSealChildCreate(BaseModel):
    name: str = Field(..., max_length=20)
    qseal_type: str = Field(..., max_length=25)
    capacity: int | None = None
    app_cascade_map: bool = False
    extra_data: dict[str, Any] | None = None


class QSealChildListResponse(BaseModel):
    children: list[QSealParentResponse]
    pagination: dict[str, Any]


# ── Map QSeals ────────────────────────────────────────────────────────────────


class QSealMapRequest(BaseModel):
    child_ids: list[UUID] = Field(
        ..., min_length=1, description="IDs of child nodes to attach"
    )


class QSealMapResponse(BaseModel):
    parent_id: UUID
    mapped_count: int
    message: str


# ── QSeal Scan ────────────────────────────────────────────────────────────────


class QSealScanRequest(BaseModel):
    serial_number: str = Field(
        ..., min_length=1, max_length=75, description="Serial number of the scanned QSeal node"
    )
    device_type: str | None = None
    os: str | None = None
    browser: str | None = None
    ip_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    street_address: str | None = None
    extra_data: dict[str, Any] | None = None


class QSealScanResponse(BaseModel):
    node_id: UUID
    serial_number: str | None
    qseal_type: str | None
    name: str | None
    parent_id: UUID | None
    parent_serial: str | None = None
    children_count: int
    message: str
    scan_event_id: UUID | None = None
    verification_status: str | None = None


# ── QSeal History ─────────────────────────────────────────────────────────────


class QSealHistoryItem(BaseModel):
    id: UUID
    organization_id: UUID
    serial_number: str | None
    product_item_id: UUID | None
    scan_timestamp: datetime
    device_type: str | None
    city: str | None
    state: str | None
    country: str | None
    street_address: str | None
    product_id: UUID | None = None
    block_id: UUID | None = None
    batch: str | None = None
    qseal_track_id: UUID | None = None
    qseal_parameter_id: UUID | None = None
    qseal_type: str | None = None
    verification_status: str | None = None
    is_suspicious: bool = False
    risk_score: int = 0
    suspicious_reasons: list[str] = Field(default_factory=list)
    review_status: str = "not_flagged"

    model_config = {"from_attributes": True}


class QSealHistoryResponse(BaseModel):
    events: list[QSealHistoryItem]
    pagination: dict[str, Any]


# ── Client-facing QSeal Analytics ────────────────────────────────────────────


class QSealAnalyticsSummaryResponse(BaseModel):
    """KPI values for the client-facing QSeal analytics Summary tab."""

    total_scans: int
    valid_scans: int
    invalid_scans: int
    unique_serials: int
    repeat_scans: int
    repeat_scan_rate: float
    suspicious_scans: int = 0
    suspicious_rate: float = 0.0
    high_risk_scans: int = 0
    unreviewed_suspicious_scans: int = 0


class QSealScanTrendItem(BaseModel):
    date: str
    total_scans: int
    valid_scans: int
    invalid_scans: int
    suspicious_scans: int = 0


class QSealScanTrendResponse(BaseModel):
    items: list[QSealScanTrendItem]


class QSealProductAnalyticsItem(BaseModel):
    product_id: UUID | None
    product_name: str
    batch: str | None
    total_scans: int
    valid_scans: int
    invalid_scans: int
    unique_serials: int
    last_scan: datetime | None


class QSealProductAnalyticsResponse(BaseModel):
    items: list[QSealProductAnalyticsItem]


class QSealGeographyAnalyticsItem(BaseModel):
    country: str | None
    state: str | None
    city: str | None
    latitude: float | None
    longitude: float | None
    total_scans: int
    valid_scans: int
    invalid_scans: int


class QSealGeographyAnalyticsResponse(BaseModel):
    items: list[QSealGeographyAnalyticsItem]


class QSealDeviceAnalyticsItem(BaseModel):
    device_type: str
    total_scans: int
    valid_scans: int
    invalid_scans: int


class QSealDeviceAnalyticsResponse(BaseModel):
    items: list[QSealDeviceAnalyticsItem]


class QSealSuspiciousScanItem(BaseModel):
    id: UUID
    organization_id: UUID
    serial_number: str | None
    product_id: UUID | None
    product_name: str
    block_id: UUID | None
    batch: str | None
    scan_timestamp: datetime
    verification_status: str | None
    is_suspicious: bool
    risk_score: int
    risk_level: Literal["normal", "review", "high"]
    suspicious_reasons: list[str] = Field(default_factory=list)
    review_status: Literal["not_flagged", "new", "reviewed", "dismissed"]
    device_type: str | None
    city: str | None
    state: str | None
    country: str | None


class QSealSuspiciousScanResponse(BaseModel):
    items: list[QSealSuspiciousScanItem]
    pagination: dict[str, Any]


class QSealSuspiciousReviewRequest(BaseModel):
    review_status: Literal["new", "reviewed", "dismissed"]


# ── Parent with Linked Units (for inbound/receiving) ──────────────────────────


class QSealLinkedUnit(BaseModel):
    """A single child unit linked to a parent QSeal."""

    id: UUID
    serial_number: str | None
    product_name: str | None = None
    product_sku: str | None = None
    manufacturing_date: str | None = None
    expiry_date: str | None = None
    manufacturing_unit: str | None = None
    dispatch_batch: str | None = None
    destination_market: str | None = None
    mrp: float | None = None
    currency: str | None = None
    batch_size: int | None = None
    qseal_cascade: bool = False
    product_item_url: str | None = None  # token_id / QR URL from ProductItem
    product_item_scan_count: int = 0
    extra_data: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class QSealParentDetailResponse(BaseModel):
    """Parent QSeal node with all linked child units."""

    id: UUID
    organization_id: UUID
    qseal_type: str | None
    name: str | None
    capacity: int | None
    serial_number: str | None
    qseal_code_link: str | None
    app_cascade_map: bool
    parent_id: UUID | None
    children_count: int
    linked_units: list[QSealLinkedUnit]
    created_at: datetime


# ── Label Download ────────────────────────────────────────────────────────────


class QSealLabelDownloadResponse(BaseModel):
    parent_id: UUID
    labels: list[dict[str, Any]]
    total: int


# ── Auto-link (automatic cascade/aggregation) ────────────────────────────────


class QSealAutoLinkRequest(BaseModel):
    """Optional master-pack size override for automatic cascading."""

    master_pack_size: int | None = Field(None, gt=0)


class QSealAutoLinkResponse(BaseModel):
    block_id: UUID
    batch: str
    master_pack_size: int
    parent_count: int
    linked_item_count: int
    message: str


# ── Aggregation log ──────────────────────────────────────────────────────────


class QSealAggregationItem(BaseModel):
    """One child unit and its aggregation (parent link) + activation state."""

    id: UUID
    block_id: UUID | None
    batch: str | None
    child_serial: str | None
    activated: bool | None
    scan_count: int
    linked: bool
    parent_id: UUID | None
    parent_serial: str | None
    parent_name: str | None
    parent_type: str | None
    parent_capacity: int | None
    parent_linked_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class QSealAggregationResponse(BaseModel):
    items: list[QSealAggregationItem]
    pagination: dict[str, Any]


class QSealAggregationChild(BaseModel):
    """A child unit nested under a parent in the grouped aggregation view."""

    id: UUID
    block_id: UUID | None
    batch: str | None
    child_serial: str | None
    activated: bool | None
    scan_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class QSealAggregationGroup(BaseModel):
    """A parent (master-pack) box with its linked child units."""

    parent_id: UUID
    parent_serial: str | None
    parent_name: str | None
    parent_type: str | None
    parent_capacity: int | None
    linked_count: int
    children: list[QSealAggregationChild]


class QSealAggregationGroupedResponse(BaseModel):
    """Grouped aggregation view — children nested under their parent box."""

    groups: list[QSealAggregationGroup]
    unlinked: list[QSealAggregationItem]
    pagination: dict[str, Any]
