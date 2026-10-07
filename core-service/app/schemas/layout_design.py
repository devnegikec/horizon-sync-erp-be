"""Pydantic schemas for the JSON Layout Designer API.

The *document* itself is validated by :mod:`app.layout_design.schema`, not here:
these are the request/response envelopes for the validate / preview / apply
endpoints. The document is carried as a plain ``dict`` so a malformed document is
reported through the diagnostics channel (``LAYOUT_DOC_INVALID``) rather than as a
422 from FastAPI, which is what lets the UI present a bad import the same way it
presents a bad dimension.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md section 6
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LayoutEntityRefOut(BaseModel):
    """A pointer back at the entity a diagnostic is about."""

    kind: str
    id: str
    label: str


class LayoutDiagnosticOut(BaseModel):
    """One structured finding about a layout document."""

    code: str
    severity: str
    message: str
    entity_refs: list[LayoutEntityRefOut] = Field(default_factory=list)
    data: dict[str, Any] | None = None


class LayoutSummaryOut(BaseModel):
    """Headline counts for the preview header and the status badge."""

    zones: int
    aisles: int
    lanes: int
    rack_types: int
    obstacles: int
    bays: int
    active_bays: int
    levels: int
    bins: int
    errors: int
    warnings: int


class LayoutZoneOut(BaseModel):
    """A derived zone."""

    code: str
    ordinal: int
    path: str
    aisle_count: int


class LayoutBinOut(BaseModel):
    """One derived storage position, with its WMS path."""

    path: str
    code: str
    label: str
    aisle_code: str
    lane_code: str
    side: str
    bay_seq: int
    level_index: int
    level_path: str
    x: float
    y: float
    z: float
    capacity_m3: float
    usable_volume_m3: float
    max_volume_cc: float
    max_weight_kg: float | None = None


class LayoutObstacleOut(BaseModel):
    """An obstacle as a box, for the plan and 3D overlay."""

    id: str
    kind: str
    x: float
    z: float
    width_m: float
    depth_m: float
    height_m: float


class LayoutAislePlanOut(BaseModel):
    """An aisle centreline, for the 2D plan."""

    code: str
    x1: float
    z1: float
    x2: float
    z2: float
    width_m: float


class LayoutPlanOut(BaseModel):
    """Everything needed to draw the document without loading it in 3D."""

    footprint_length_m: float
    footprint_width_m: float
    aisles: list[LayoutAislePlanOut] = Field(default_factory=list)
    obstacles: list[LayoutObstacleOut] = Field(default_factory=list)


class LayoutValidateRequest(BaseModel):
    """A document to validate. Nothing is written."""

    document: dict[str, Any]


class LayoutValidateResponse(BaseModel):
    """The compiler's verdict on a document."""

    valid: bool
    applyable: bool
    summary: LayoutSummaryOut
    diagnostics: list[LayoutDiagnosticOut] = Field(default_factory=list)
    sample_bin_paths: list[str] = Field(default_factory=list)


class LayoutPreviewRequest(BaseModel):
    """A document to preview, with how many bins to return."""

    document: dict[str, Any]
    limit: int = Field(default=25, ge=0, le=500)


class LayoutPreviewResponse(LayoutValidateResponse):
    """The verdict plus enough geometry to render the document."""

    zones: list[LayoutZoneOut] = Field(default_factory=list)
    bins: list[LayoutBinOut] = Field(default_factory=list)
    plan: LayoutPlanOut


class LayoutApplyRequest(BaseModel):
    """Persist a document as the warehouse's location hierarchy."""

    warehouse_id: UUID
    document: dict[str, Any]
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    replace_existing: bool = False


class LayoutApplyResponse(BaseModel):
    """What the apply actually wrote."""

    floor_plan_id: UUID
    locations_created: int
    locations_updated: int
    locations_deactivated: int
    summary: LayoutSummaryOut
    sample_bin_paths: list[str] = Field(default_factory=list)
    # Non-blocking findings, e.g. `BIN_OVER_CAPACITY_AFTER_APPLY` when the new
    # limits leave an already-stocked bin below its contents.
    diagnostics: list[LayoutDiagnosticOut] = Field(default_factory=list)


class LayoutRuleOut(BaseModel):
    """A registered diagnostic rule."""

    code: str
    severity: str
    description: str


class LayoutExampleOut(BaseModel):
    """An import template."""

    name: str
    document: dict[str, Any]
