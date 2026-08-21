"""Pydantic schemas for warehouse capacity endpoints."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VolumeCapacity(BaseModel):
    occupied_m3: Decimal = Decimal("0")
    capacity_m3: Decimal | None = None
    pct: Decimal | None = None


class WeightCapacity(BaseModel):
    occupied_kg: Decimal = Decimal("0")
    capacity_kg: Decimal | None = None
    pct: Decimal | None = None


class BinCapacityResponse(BaseModel):
    bin_id: UUID
    warehouse_id: UUID
    code: str
    full_path: str | None = None
    volume: VolumeCapacity
    weight: WeightCapacity
    binding_pct: Decimal
    bin_state: str
    is_available: bool

    model_config = ConfigDict(from_attributes=False)


class CapacityTreeNode(BaseModel):
    node: str
    level: str
    code: str
    full_path: str | None = None
    volume: VolumeCapacity
    weight: WeightCapacity
    binding_pct: Decimal | None = None
    bin_state: str | None = None
    is_available: bool | None = None
    children: list[CapacityTreeNode] = []


class BinStateResponse(BaseModel):
    bin_id: UUID
    code: str
    position_x: Decimal = Decimal("0")
    position_y: Decimal = Decimal("0")
    position_z: Decimal = Decimal("0")
    qr_code: str | None = None
    bin_state: str
    binding_pct: Decimal | None = None
    is_available: bool


class AvailableBinResponse(BaseModel):
    bin_id: UUID
    code: str
    full_path: str | None = None
    bin_state: str
    binding_pct: Decimal | None = None
    is_available: bool


CapacityTreeNode.model_rebuild()
