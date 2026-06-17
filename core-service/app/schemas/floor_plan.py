"""Pydantic schemas for the Floor Plan Designer API.

The FloorPlanConfig is serialised to JSONB in the warehouse_floor_plans table
and is also the input to FloorPlanGeneratorService.generate().

Naming: world coordinates are in dimensionless grid units; the grid_unit field
on FloorPlanConfig carries the real-world metres-per-unit scale (used only for
display labels — the 3D renderer treats units as-is).
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ─── Config schemas (stored in DB + used as generator input) ──────────────────

class BinSpec(BaseModel):
    """Overrides applied to individual bins (optional; most come from AisleSpec)."""
    capacity: float | None = None


class AisleSpec(BaseModel):
    """Single aisle specification inside a zone."""
    code: str
    name: str | None = None
    orientation: Literal["x", "y"] = "x"
    grid_x: float = 0.0
    grid_y: float = 0.0
    num_bays: Annotated[int, Field(ge=1, le=200)] = 4
    bay_spacing: Annotated[float, Field(gt=0)] = 1.5
    num_levels: Annotated[int, Field(ge=1, le=20)] = 3
    bins_per_level: Annotated[int, Field(ge=1, le=10)] = 1
    bin_capacity: Annotated[float, Field(gt=0)] = 100.0


class ZoneSpec(BaseModel):
    """Single zone specification."""
    code: str
    name: str | None = None
    grid_x: float = 0.0
    grid_y: float = 0.0
    aisles: list[AisleSpec] = Field(default_factory=list)


class FloorPlanConfig(BaseModel):
    """Top-level layout configuration — stored as JSONB in the DB."""
    grid_unit: Annotated[float, Field(gt=0)] = 1.0
    zones: list[ZoneSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_unique_codes(self) -> FloorPlanConfig:
        zone_codes = [z.code for z in self.zones]
        if len(zone_codes) != len(set(zone_codes)):
            raise ValueError("Zone codes must be unique within a floor plan")
        for zone in self.zones:
            aisle_codes = [a.code for a in zone.aisles]
            if len(aisle_codes) != len(set(aisle_codes)):
                raise ValueError(
                    f"Aisle codes must be unique within zone '{zone.code}'"
                )
        return self


# ─── Request / Response schemas ───────────────────────────────────────────────

class FloorPlanPreviewRequest(BaseModel):
    warehouse_id: UUID
    config: FloorPlanConfig


class GeneratedLocationSummary(BaseModel):
    zone_count: int
    aisle_count: int
    bay_count: int
    level_count: int
    bin_count: int
    sample_bin_codes: list[str]


class FloorPlanPreviewResponse(BaseModel):
    warehouse_id: UUID
    summary: GeneratedLocationSummary
    config: FloorPlanConfig


class FloorPlanApplyRequest(BaseModel):
    warehouse_id: UUID
    name: str
    description: str | None = None
    config: FloorPlanConfig
    replace_existing: bool = False


class FloorPlanResponse(BaseModel):
    id: UUID
    warehouse_id: UUID
    name: str
    description: str | None
    config: FloorPlanConfig
    generated_at: str | None
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class FloorPlanApplyResponse(BaseModel):
    floor_plan_id: UUID
    locations_created: int
    locations_deleted: int
    summary: GeneratedLocationSummary
