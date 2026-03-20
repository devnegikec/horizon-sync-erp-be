"""Pydantic schemas for Cascade / Hierarchical QR module"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Parent QR ─────────────────────────────────────────────────────────────────

class ParentQRCreate(BaseModel):
    name: str = Field(..., max_length=20, description="Label for this parent node, e.g. 'Pallet'")
    qr_type: str = Field(..., max_length=25, description="e.g. pallet, carton, box")
    capacity: int = Field(..., gt=0, description="Max number of child QRs this node can hold")
    app_cascade_map: bool = False
    extra_data: dict[str, Any] | None = None


class ParentQRResponse(BaseModel):
    id: UUID
    organization_id: UUID
    qr_type: str | None
    name: str | None
    capacity: int | None
    serial_number: str | None
    qr_code_link: str | None
    app_cascade_map: bool
    parent_id: UUID | None
    parent_app_id: UUID | None
    children_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class ParentQRListResponse(BaseModel):
    nodes: list[ParentQRResponse]
    pagination: dict[str, Any]


# ── Child QR ──────────────────────────────────────────────────────────────────

class ChildQRCreate(BaseModel):
    name: str = Field(..., max_length=20)
    qr_type: str = Field(..., max_length=25)
    capacity: int | None = None
    app_cascade_map: bool = False
    extra_data: dict[str, Any] | None = None


class ChildQRListResponse(BaseModel):
    children: list[ParentQRResponse]
    pagination: dict[str, Any]


# ── Map QRs ───────────────────────────────────────────────────────────────────

class MapQRRequest(BaseModel):
    child_ids: list[UUID] = Field(..., min_length=1, description="IDs of child nodes to attach")


class MapQRResponse(BaseModel):
    parent_id: UUID
    mapped_count: int
    message: str


# ── Cascade Scan ──────────────────────────────────────────────────────────────

class CascadeScanRequest(BaseModel):
    serial_number: str = Field(..., description="Serial number of the scanned QR node")
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


class CascadeScanResponse(BaseModel):
    node_id: UUID
    serial_number: str | None
    qr_type: str | None
    name: str | None
    parent_id: UUID | None
    children_count: int
    message: str


# ── Cascade History ───────────────────────────────────────────────────────────

class CascadeHistoryItem(BaseModel):
    id: UUID
    organization_id: UUID
    serial_number: str | None
    product_item_id: UUID | None
    scan_timestamp: datetime
    device_type: str | None
    city: str | None
    state: str | None
    country: str | None

    model_config = {"from_attributes": True}


class CascadeHistoryResponse(BaseModel):
    events: list[CascadeHistoryItem]
    pagination: dict[str, Any]


# ── Label Download ────────────────────────────────────────────────────────────

class LabelDownloadResponse(BaseModel):
    parent_id: UUID
    labels: list[dict[str, Any]]
    total: int
