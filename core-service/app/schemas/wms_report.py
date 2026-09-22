"""Pydantic schemas for WMS report responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import PaginationMeta


# ── 1. Stock movement report ───────────────────────────────────────────────


class StockMovementSummary(BaseModel):
    total_in_qty: float = 0
    total_in_value: float = 0
    total_out_qty: float = 0
    total_out_value: float = 0
    total_transfer_qty: float = 0
    total_adjustment_qty: float = 0


class StockMovementRow(BaseModel):
    id: UUID
    performed_at: datetime | None
    movement_type: str
    quantity: float
    unit_cost: float | None
    line_value: float
    reference_type: str | None
    reference_id: UUID | None
    notes: str | None
    warehouse_id: UUID | None
    warehouse_name: str | None
    item_id: UUID | None
    item_code: str | None
    item_name: str | None
    sku: str | None


class StockMovementReportResponse(BaseModel):
    summary: StockMovementSummary
    rows: list[StockMovementRow]
    pagination: PaginationMeta


# ── 2. Inventory aging report ──────────────────────────────────────────────


class InventoryAgingSummary(BaseModel):
    idle_item_count: int = 0
    total_idle_qty: float = 0
    total_idle_value: float = 0
    days_idle: int


class InventoryAgingRow(BaseModel):
    item_id: UUID
    item_code: str | None
    item_name: str | None
    sku: str | None
    warehouse_id: UUID | None
    warehouse_name: str | None
    quantity_on_hand: float
    quantity_reserved: float
    quantity_available: float
    last_moved_at: datetime | None
    last_unit_cost: float | None
    est_value: float
    days_idle: int | None


class InventoryAgingReportResponse(BaseModel):
    summary: InventoryAgingSummary
    rows: list[InventoryAgingRow]
    pagination: PaginationMeta


# ── 3. Receiving vs ASN variance report ────────────────────────────────────


class ReceivingVarianceSummary(BaseModel):
    total_expected_qty: float = 0
    total_received_qty: float = 0
    total_variance_qty: float = 0
    line_count: int = 0
    short_line_count: int = 0
    excess_line_count: int = 0


class ReceivingVarianceRow(BaseModel):
    asn_order_id: UUID
    asn_order_no: str | None
    order_date: datetime | None
    asn_status: str | None
    warehouse_id: UUID | None
    warehouse_name: str | None
    item_id: UUID
    item_code: str | None
    item_name: str | None
    sku: str | None
    expected_qty: float
    received_qty: float
    variance_qty: float


class ReceivingVarianceReportResponse(BaseModel):
    summary: ReceivingVarianceSummary
    rows: list[ReceivingVarianceRow]
    pagination: PaginationMeta


# ── 4. Bin capacity utilization report ─────────────────────────────────────


class BinCapacitySummary(BaseModel):
    total_bins: int = 0
    bins_with_volume_capacity: int = 0
    bins_with_weight_capacity: int = 0
    total_capacity_cc: float = 0
    total_occupied_cc: float = 0
    volume_utilization_pct: float | None = None
    total_capacity_grams: float = 0
    total_occupied_grams: float = 0
    weight_utilization_pct: float | None = None
    over_utilized_bins: int = 0
    full_bins: int = 0


class BinCapacityRow(BaseModel):
    bin_id: UUID
    code: str | None
    full_path: str | None
    location_type: str | None
    is_pickable: bool
    unit_count: float
    master_pack_count: float
    occupied_cc: float
    capacity_cc: float | None
    volume_utilization_pct: float | None
    occupied_grams: float
    capacity_grams: float | None
    weight_utilization_pct: float | None


class BinCapacityReportResponse(BaseModel):
    summary: BinCapacitySummary
    rows: list[BinCapacityRow]
    pagination: PaginationMeta
