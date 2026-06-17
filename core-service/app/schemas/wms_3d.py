"""Pydantic schemas for the 3D Warehouse View & Smart Location Engine API.

Design ref: docs/3D_WAREHOUSE_VIEW_DESIGN.md section 5
"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# ===========================================
# SHARED
# ===========================================


class Position3D(BaseModel):
    x: float = 0
    y: float = 0
    z: float = 0


# ===========================================
# LAYOUT (5.1)
# ===========================================


class LayoutWarehouse(BaseModel):
    id: UUID
    name: str
    code: str


class LayoutBin(BaseModel):
    id: UUID
    code: str
    full_path: str | None = None
    position: Position3D
    capacity: float
    available_capacity: float
    fill_percentage: float
    is_active: bool = True
    is_reserved: bool
    reserved_by_worker_id: UUID | None = None
    items_count: int
    has_expiring_items: bool


class LayoutLevel(BaseModel):
    id: UUID
    code: str
    name: str | None = None
    position: Position3D
    bins: list[LayoutBin] = Field(default_factory=list)


class LayoutBay(BaseModel):
    id: UUID
    code: str
    name: str | None = None
    position: Position3D
    levels: list[LayoutLevel] = Field(default_factory=list)


class LayoutAisle(BaseModel):
    id: UUID
    code: str
    name: str | None = None
    position: Position3D
    orientation: str | None = None
    bays: list[LayoutBay] = Field(default_factory=list)


class LayoutZone(BaseModel):
    id: UUID
    code: str
    name: str | None = None
    position: Position3D
    aisles: list[LayoutAisle] = Field(default_factory=list)


class LayoutResponse(BaseModel):
    warehouse: LayoutWarehouse
    zones: list[LayoutZone] = Field(default_factory=list)


# ===========================================
# LIVE STATUS (5.2)
# ===========================================


class StatusReservedBy(BaseModel):
    worker_id: UUID
    expires_in_seconds: int


class StatusBin(BaseModel):
    bin_id: UUID
    fill_percentage: float
    is_reserved: bool
    reserved_by: StatusReservedBy | None = None


class StatusWorker(BaseModel):
    worker_id: UUID
    name: str | None = None
    current_bin_id: UUID | None = None
    task_type: str | None = None
    last_scan_at: str | None = None


class StatusResponse(BaseModel):
    bins: list[StatusBin] = Field(default_factory=list)
    workers: list[StatusWorker] = Field(default_factory=list)


# ===========================================
# SUGGEST (5.3)
# ===========================================


class SuggestRequest(BaseModel):
    task_type: str = Field(..., description="'put_away' or 'pick'")
    item_id: UUID
    quantity: Decimal = Field(..., gt=0)
    warehouse_id: UUID
    worker_id: UUID
    batch_number: str | None = None
    exclude_bin_ids: list[UUID] = Field(default_factory=list)
    worker_position: Position3D | None = None
    limit: int = Field(10, ge=1, le=50)


class Suggestion(BaseModel):
    rank: int
    bin_id: UUID
    bin_code: str | None = None
    position: Position3D
    score: float
    reasons: list[str] = Field(default_factory=list)
    available_capacity: float
    distance_from_worker: float
    estimated_time_seconds: int
    batch_number: str | None = None
    expiry_date: str | None = None


class SuggestResponse(BaseModel):
    suggestions: list[Suggestion] = Field(default_factory=list)
    strategy_used: str
    total_candidates_evaluated: int
    excluded_bins: int


# ===========================================
# RESERVE / RELEASE (5.4, 5.5)
# ===========================================


class ReserveRequest(BaseModel):
    bin_id: UUID
    worker_id: UUID
    task_id: UUID | None = None
    task_type: str | None = Field(None, description="'put_away' or 'pick'")
    ttl_seconds: int = Field(300, gt=0)


class ReservationResponse(BaseModel):
    id: UUID
    bin_id: UUID
    worker_id: UUID
    task_id: UUID | None = None
    task_type: str | None = None
    reserved_at: str
    expires_at: str
    expires_in_seconds: int


class ReleaseRequest(BaseModel):
    bin_id: UUID
    worker_id: UUID


class ReleaseResponse(BaseModel):
    released: bool
    bin_id: UUID


# ===========================================
# BIN STOCK DETAIL (FR-3D-04)
# ===========================================


class BinStockItem(BaseModel):
    """Individual item record stored in a bin."""

    item_id: UUID
    item_name: str
    item_code: str
    sku: str | None = None
    quantity_on_hand: float
    batch_number: str | None = None
    expiry_date: str | None = None
    uom: str | None = None
    created_at: str | None = None


class BinStockDetailResponse(BaseModel):
    """Detailed stock breakdown for a single bin (items, batches, expiry)."""

    bin_id: UUID
    bin_code: str | None = None
    items: list[BinStockItem] = Field(default_factory=list)
    total_quantity: float = 0
    total_items: int = 0
