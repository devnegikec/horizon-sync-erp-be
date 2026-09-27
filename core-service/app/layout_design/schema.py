"""Layout document (v1) — the JSON input format for the warehouse designer.

The document **is** the input format: there is no separate import schema and no
translation layer. It is produced by the frontend designer, hand-written by a
warehouse engineer, or exported from an existing design, then compiled by
:mod:`app.layout_design.compile` before anything is persisted.

Units are **metres everywhere**, matching ``WarehouseLocation.position_x/y/z``
and the frontend renderer.

Two deliberate choices:

* **camelCase field names.** The wire contract keeps the camelCase shape the
  designer already emits, and the *same* JSON is compiled by the TypeScript
  engine in the frontend. Using the field names directly as the contract (rather
  than snake_case attributes plus aliases) means the two compilers cannot drift
  on spelling.
* **Bins are never authored.** The document describes racking, levels and runs;
  bays and bins are derived by the compiler, so the two can never disagree.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md section 3
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.layout_design.geometry import DEFAULT_UTILIZATION
from app.layout_design.naming import (
    DEFAULT_BIN_CODE_PATTERN,
    NamingScheme,
    is_valid_code_pattern,
)

#: The document version this build compiles.
CURRENT_SCHEMA_VERSION = 1

#: Fallback zone code when an aisle does not declare ``zoneCode``.
DEFAULT_ZONE_CODE = "01"

Positive = Annotated[float, Field(gt=0)]
NonNegative = Annotated[float, Field(ge=0)]


class LayoutOrigin(BaseModel):
    """Floor-level origin corner of the building."""

    x: float = 0.0
    z: float = 0.0


class RackLevel(BaseModel):
    """One shelf level of a lane.

    Levels are **per lane**, so two lanes of one aisle can differ in count,
    clear height and depth.
    """

    clearHeightM: Positive
    binDepthM: Positive
    beamHeightM: NonNegative = 0.08
    maxWeightKg: Positive | None = None

    @property
    def stackHeightM(self) -> float:
        """Pitch consumed by this level: beam plus clear opening."""
        return self.beamHeightM + self.clearHeightM


class RackType(BaseModel):
    """The physical racking: bay pitch and how far the frame reaches out."""

    id: str = Field(min_length=1)
    code: str = Field(min_length=1)
    name: str = ""
    bayWidthM: Positive
    depthM: Positive
    uprightWidthM: Positive = 0.12
    uprightDepthM: Positive = 0.12
    metadata: dict[str, Any] = Field(default_factory=dict)


class LaneSegment(BaseModel):
    """A RACK or GAP run, measured in metres along the lane."""

    kind: Literal["RACK", "GAP"]
    startM: NonNegative
    endM: Positive
    label: str | None = None

    @model_validator(mode="after")
    def _check_ordering(self) -> LaneSegment:
        if self.endM <= self.startM:
            raise ValueError("Lane segment endM must be greater than startM")
        return self


class LaneCenterline(BaseModel):
    """Aisle centreline. v1 supports exactly axis-aligned runs."""

    x1: float
    z1: float
    x2: float
    z2: float

    @property
    def deltaX(self) -> float:
        return self.x2 - self.x1

    @property
    def deltaZ(self) -> float:
        return self.z2 - self.z1


class Lane(BaseModel):
    """One rack row on one side of an aisle."""

    id: str | None = None
    code: str = Field(min_length=1)
    side: Literal["LEFT", "RIGHT"]
    rackTypeId: str = Field(min_length=1)
    startOffsetM: NonNegative = 0.0
    lengthM: Positive
    levels: list[RackLevel] = Field(min_length=1)
    segments: list[LaneSegment] | None = None
    skipBays: list[int] = Field(default_factory=list)
    binCodePattern: str = DEFAULT_BIN_CODE_PATTERN
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("binCodePattern")
    @classmethod
    def _check_pattern(cls, value: str) -> str:
        if not is_valid_code_pattern(value):
            raise ValueError(
                "binCodePattern must contain at least one placeholder and only use "
                "{warehouse} {aisle} {lane} {side} {bay} {level}"
            )
        return value

    @field_validator("skipBays")
    @classmethod
    def _check_skip_bays(cls, value: list[int]) -> list[int]:
        for bay in value:
            if bay < 1:
                raise ValueError("skipBays entries are 1-based bay numbers")
        return value

    @property
    def resolvedSegments(self) -> list[LaneSegment]:
        """The lane's runs, materialising the implicit single RACK run.

        Mirrors ``defaultLaneSegments`` in the TypeScript engine: an omitted
        ``segments`` means one continuous RACK run covering ``lengthM``, and it
        is materialised at every entry point so a document cannot have two
        readings.
        """
        if self.segments:
            return self.segments
        return [LaneSegment(kind="RACK", startM=0.0, endM=self.lengthM)]


class Aisle(BaseModel):
    """A corridor: a clear width between two rack faces, plus its lanes."""

    id: str | None = None
    code: str = Field(min_length=1)
    zoneCode: str | None = None
    orientation: Literal["X", "Z"]
    centerline: LaneCenterline
    widthM: Positive
    travelDirection: Literal["BOTH", "FORWARD", "REVERSE"] = "BOTH"
    lanes: list[Lane] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Obstacle(BaseModel):
    """A pillar, column, wall, office or other axis-aligned obstruction."""

    id: str | None = None
    kind: Literal["COLUMN", "PILLAR", "WALL", "OFFICE", "CUSTOM"] = "CUSTOM"
    x: float
    z: float
    widthM: Positive
    depthM: Positive
    heightM: Positive
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def label(self) -> str:
        return self.id or f"{self.kind}@({self.x},{self.z})"


class LayoutWarehouse(BaseModel):
    """The building envelope being filled."""

    id: str | None = None
    code: str = Field(min_length=1)
    name: str = ""
    lengthM: Positive
    widthM: Positive
    heightM: Positive
    origin: LayoutOrigin = Field(default_factory=LayoutOrigin)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LayoutOptions(BaseModel):
    """Document-level options that are not geometry."""

    namingScheme: NamingScheme = "wms_typed"
    defaultZoneCode: str = DEFAULT_ZONE_CODE
    utilization: Positive = DEFAULT_UTILIZATION


class LayoutDoc(BaseModel):
    """The layout document (v1)."""

    schemaVersion: int = CURRENT_SCHEMA_VERSION
    layout: LayoutOptions = Field(default_factory=LayoutOptions)
    warehouse: LayoutWarehouse
    rackTypes: list[RackType] = Field(default_factory=list)
    obstacles: list[Obstacle] = Field(default_factory=list)
    aisles: list[Aisle] = Field(default_factory=list)

    def zone_code_for(self, aisle: Aisle) -> str:
        """The zone code an aisle belongs to (its own, else the document default)."""
        return aisle.zoneCode or self.layout.defaultZoneCode

    @property
    def rack_type_by_id(self) -> dict[str, RackType]:
        return {rack_type.id: rack_type for rack_type in self.rackTypes}


# ===========================================
# HELPERS
# ===========================================


def floor_count(value: float, pitch: float) -> int:
    """Bays that fit in ``value`` metres at ``pitch`` metre centres."""
    if pitch <= 0:
        return 0
    return int((value + 1e-4) // pitch)
