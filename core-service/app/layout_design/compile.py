"""Layout document compiler.

``build_layout(document)`` turns a layout document into bays, bins, WMS location
paths and a diagnostics list. It is **pure and deterministic**: no database, no
clock, no randomness — the same document always produces the same output.

Mirrors the TypeScript engine in
``apps/inventory/src/app/features/layout-designer/layout-core/compile.ts``. The
two are kept honest by shared fixture files that both test suites assert against,
each comparing the *full* diagnostics list (code, severity, order) so a
divergence fails loudly on one side.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md sections 3, 4 and 5
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.layout_design import naming
from app.layout_design.geometry import (
    AABB,
    CC_PER_M3,
    DEFAULT_UTILIZATION,
    EPS,
    MAX_DIAGNOSTICS_PER_CODE,
    MIN_AISLE_WIDTH_M,
    aabb,
    contains,
    is_axis_aligned,
    normalize2,
    oriented_rect_aabb,
    overlap_area,
    overlaps,
    perpendicular_left,
    perpendicular_right,
    round_metric,
)
from app.layout_design.rules import (
    DIAGNOSTICS_TRUNCATED,
    LAYOUT_DOC_INVALID,
    SCHEMA_VERSION_UNSUPPORTED,
    get_rule,
)
from app.layout_design.schema import (
    CURRENT_SCHEMA_VERSION,
    Aisle,
    Lane,
    LayoutDoc,
    RackType,
    floor_count,
)

# ===========================================
# DIAGNOSTICS
# ===========================================


@dataclass(frozen=True)
class EntityRef:
    """A pointer back at the entity a diagnostic is about."""

    kind: str
    id: str
    label: str


@dataclass(frozen=True)
class Diagnostic:
    """One structured finding about a layout document."""

    code: str
    severity: str
    message: str
    entityRefs: tuple[EntityRef, ...] = ()
    data: dict[str, Any] | None = None


class DiagnosticCollector:
    """Collects diagnostics, de-duplicating floods.

    One bad parameter on a 1,500-bin document must not emit 1,500 messages, so
    repeats of the same code are capped and summarised by a single
    ``DIAGNOSTICS_TRUNCATED`` warning.
    """

    def __init__(self, max_per_code: int = MAX_DIAGNOSTICS_PER_CODE) -> None:
        self._max_per_code = max_per_code
        self._items: list[Diagnostic] = []
        self._counts: dict[str, int] = {}
        self._truncated: dict[str, int] = {}

    def error(
        self,
        code: str,
        message: str,
        entity_refs: tuple[EntityRef, ...] | list[EntityRef] = (),
        data: dict[str, Any] | None = None,
    ) -> None:
        """Report an error (the registry must agree that the code is an error)."""
        self._add(code, "error", message, entity_refs, data)

    def warn(
        self,
        code: str,
        message: str,
        entity_refs: tuple[EntityRef, ...] | list[EntityRef] = (),
        data: dict[str, Any] | None = None,
    ) -> None:
        """Report a warning (the registry must agree that the code is a warning)."""
        self._add(code, "warning", message, entity_refs, data)

    def _add(
        self,
        code: str,
        severity: str,
        message: str,
        entity_refs: tuple[EntityRef, ...] | list[EntityRef],
        data: dict[str, Any] | None,
    ) -> None:
        rule = get_rule(code)
        if rule.severity != severity:
            raise ValueError(
                f"Rule {code} is registered as '{rule.severity}' "
                f"but was reported as '{severity}'"
            )
        seen = self._counts.get(code, 0)
        self._counts[code] = seen + 1
        if seen >= self._max_per_code:
            self._truncated[code] = self._counts[code]
            return
        self._items.append(
            Diagnostic(
                code=code,
                severity=rule.severity,
                message=message,
                entityRefs=tuple(entity_refs),
                data=data,
            )
        )

    @property
    def has_errors(self) -> bool:
        return any(item.severity == "error" for item in self._items)

    def all(self) -> list[Diagnostic]:
        """Every collected diagnostic, with truncation summaries appended."""
        items = list(self._items)
        for code, total in self._truncated.items():
            items.append(
                Diagnostic(
                    code=DIAGNOSTICS_TRUNCATED.code,
                    severity=DIAGNOSTICS_TRUNCATED.severity,
                    message=(
                        f"{total} instances of {code} were suppressed after the "
                        f"first {self._max_per_code}"
                    ),
                    entityRefs=(),
                    data={"code": code, "suppressed": total - self._max_per_code},
                )
            )
        return items

    def counts(self) -> dict[str, int]:
        """Error and warning counts, for a status badge."""
        errors = sum(1 for item in self._items if item.severity == "error")
        warnings = len(self._items) - errors
        return {"errors": errors, "warnings": warnings}


# ===========================================
# COMPILED SHAPES
# ===========================================


@dataclass(frozen=True)
class CompiledZone:
    """A zone, derived from the aisles' ``zoneCode`` values."""

    code: str
    codeValue: str
    ordinal: int
    path: str
    aisleCount: int


@dataclass(frozen=True)
class CompiledBay:
    """One bay of one rack lane — a position along a rack row.

    Careful with the word "bay": here it is the *document* sense, a position
    along the aisle. In the WMS hierarchy the ``bay`` location is the **rack row
    itself** (the lane), matching ``FloorPlanGeneratorService``'s ``B01``/``B02``
    side codes, and each of these positions becomes a **bin** under a level.
    That mapping is what keeps the document's bin count equal to the WMS bin
    count.
    """

    zoneCode: str
    aisleId: str
    aisleCode: str
    laneCode: str
    side: str
    seq: int
    isSkipped: bool
    inRackRun: bool
    centerX: float
    centerZ: float
    widthM: float
    depthM: float
    rotationDeg: int
    zonePath: str
    aislePath: str
    path: str
    code: str


@dataclass(frozen=True)
class CompiledBin:
    """One storage position, with its WMS path and physical limits."""

    label: str
    warehouseCode: str
    zoneCode: str
    aisleCode: str
    laneCode: str
    side: str
    baySeq: int
    levelIndex: int
    centerX: float
    centerY: float
    centerZ: float
    widthM: float
    heightM: float
    depthM: float
    rotationDeg: int
    capacityM3: float
    usableVolumeM3: float
    maxVolumeCc: float
    maxWeightKg: float | None
    levelPath: str
    path: str
    code: str


@dataclass
class CompiledLayout:
    """The result of compiling a document."""

    doc: LayoutDoc | None
    zones: list[CompiledZone] = field(default_factory=list)
    bays: list[CompiledBay] = field(default_factory=list)
    bins: list[CompiledBin] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def errorCount(self) -> int:
        return sum(1 for item in self.diagnostics if item.severity == "error")

    @property
    def warningCount(self) -> int:
        return sum(1 for item in self.diagnostics if item.severity == "warning")

    @property
    def applyable(self) -> bool:
        """True when the document may be persisted (no blocking diagnostics)."""
        return self.errorCount == 0

    @property
    def activeBays(self) -> list[CompiledBay]:
        return [bay for bay in self.bays if bay.inRackRun and not bay.isSkipped]

    def summary(self) -> dict[str, int]:
        """Headline counts for a preview panel or a real-time badge."""
        return {
            "zones": len(self.zones),
            "aisles": len(self.doc.aisles) if self.doc else 0,
            "lanes": sum(len(aisle.lanes) for aisle in self.doc.aisles)
            if self.doc
            else 0,
            "rackTypes": len(self.doc.rackTypes) if self.doc else 0,
            "obstacles": len(self.doc.obstacles) if self.doc else 0,
            "bays": len(self.bays),
            "activeBays": len(self.activeBays),
            "levels": sum(
                len(lane.levels)
                for aisle in (self.doc.aisles if self.doc else [])
                for lane in aisle.lanes
            ),
            "bins": len(self.bins),
            "errors": self.errorCount,
            "warnings": self.warningCount,
        }

    def sampleBinPaths(self, limit: int = 8) -> list[str]:
        """The first ``limit`` bin paths, so a designer can confirm naming."""
        return [bin_.path for bin_ in self.bins[:limit]]


# ===========================================
# PARSING
# ===========================================


def parse_document(
    raw: dict[str, Any] | LayoutDoc,
) -> tuple[LayoutDoc | None, list[Diagnostic]]:
    """Validate raw JSON into a :class:`LayoutDoc`.

    Args:
        raw: The parsed JSON document, or an already-validated document.

    Returns:
        ``(document, diagnostics)``. On a structural failure the document is
        ``None`` and diagnostics carries a single ``LAYOUT_DOC_INVALID`` error
        rather than raising, so a bad file can be reported in the UI the same way
        as any other diagnostic.
    """
    if isinstance(raw, LayoutDoc):
        return raw, []

    try:
        return LayoutDoc.model_validate(raw), []
    except ValidationError as exc:
        problems = []
        for error in exc.errors()[:5]:
            location = ".".join(str(part) for part in error["loc"]) or "<root>"
            problems.append(f"{location}: {error['msg']}")
        return None, [
            Diagnostic(
                code=LAYOUT_DOC_INVALID.code,
                severity=LAYOUT_DOC_INVALID.severity,
                message="; ".join(problems),
                entityRefs=(),
                data={"errorCount": len(exc.errors())},
            )
        ]


# ===========================================
# COMPILER
# ===========================================


def build_layout(raw: dict[str, Any] | LayoutDoc) -> CompiledLayout:
    """Compile a layout document into bays, bins, WMS paths and diagnostics.

    Never raises for malformed input: a document that cannot be parsed, or whose
    ``schemaVersion`` is unsupported, comes back as an empty layout carrying the
    relevant error diagnostic.
    """
    doc, parse_errors = parse_document(raw)
    if doc is None:
        return CompiledLayout(doc=None, diagnostics=parse_errors)

    if doc.schemaVersion != CURRENT_SCHEMA_VERSION:
        return CompiledLayout(
            doc=doc,
            diagnostics=[
                Diagnostic(
                    code=SCHEMA_VERSION_UNSUPPORTED.code,
                    severity=SCHEMA_VERSION_UNSUPPORTED.severity,
                    message=(
                        f"Document schemaVersion {doc.schemaVersion} is not supported; "
                        f"this build compiles version {CURRENT_SCHEMA_VERSION}"
                    ),
                    entityRefs=(),
                    data={"schemaVersion": doc.schemaVersion},
                )
            ],
        )

    collector = DiagnosticCollector()
    zones, bays, bins = _compile(doc, collector)
    return CompiledLayout(
        doc=doc,
        zones=zones,
        bays=bays,
        bins=bins,
        diagnostics=collector.all(),
    )


def _compile(
    doc: LayoutDoc,
    collector: DiagnosticCollector,
) -> tuple[list[CompiledZone], list[CompiledBay], list[CompiledBin]]:
    """Derive zones, bays and bins, reporting diagnostics as it goes."""
    warehouse = doc.warehouse
    scheme = doc.layout.namingScheme
    utilization = doc.layout.utilization or DEFAULT_UTILIZATION

    footprint = aabb(
        warehouse.origin.x,
        warehouse.origin.z,
        warehouse.origin.x + warehouse.lengthM,
        warehouse.origin.z + warehouse.widthM,
    )
    warehouse_ref = EntityRef(
        kind="warehouse", id=warehouse.id or warehouse.code, label=warehouse.code
    )

    rack_types = doc.rack_type_by_id
    if not rack_types and any(aisle.lanes for aisle in doc.aisles):
        collector.error(
            "NO_RACK_TYPES_DEFINED",
            "Aisles have lanes but the document defines no rack types",
            [warehouse_ref],
        )

    obstacle_rects = [
        (
            obstacle,
            aabb(
                obstacle.x,
                obstacle.z,
                obstacle.x + obstacle.widthM,
                obstacle.z + obstacle.depthM,
            ),
        )
        for obstacle in doc.obstacles
    ]

    zone_ordinals, zone_aisle_counts = _zone_ordinals(doc, collector)

    zones: list[CompiledZone] = []
    for code in zone_ordinals:
        ordinal = zone_ordinals[code]
        path = naming.wms_segment("zone", ordinal, code, scheme)
        zones.append(
            CompiledZone(
                code=code,
                codeValue=code,
                ordinal=ordinal,
                path=path,
                aisleCount=zone_aisle_counts.get(code, 0),
            )
        )

    bays: list[CompiledBay] = []
    bins: list[CompiledBin] = []
    bay_rects: list[tuple[str, AABB]] = []
    code_counts: dict[str, int] = {}
    code_first_seen: dict[str, EntityRef] = {}
    seen_aisle_codes: set[str] = set()

    for aisle_index, aisle in enumerate(doc.aisles, start=1):
        aisle_ref = EntityRef(kind="aisle", id=aisle.id or aisle.code, label=aisle.code)

        if aisle.code in seen_aisle_codes:
            collector.error(
                "AISLE_CODE_DUPLICATE",
                f"Aisle code '{aisle.code}' is used more than once",
                [aisle_ref],
            )
        seen_aisle_codes.add(aisle.code)

        forward = normalize2(aisle.centerline.deltaX, aisle.centerline.deltaZ)
        if forward is None:
            collector.error(
                "AISLE_ZERO_LENGTH",
                f"Aisle '{aisle.code}' has a zero-length centerline",
                [aisle_ref],
            )
            continue
        if not is_axis_aligned(forward):
            collector.error(
                "AISLE_NOT_AXIS_ALIGNED",
                f"Aisle '{aisle.code}' must run exactly along X or Z; v1 does not "
                "support diagonal aisles",
                [aisle_ref],
            )
            continue

        derived_orientation = "X" if abs(forward[0]) > abs(forward[1]) else "Z"
        if derived_orientation != aisle.orientation:
            collector.error(
                "AISLE_ORIENTATION_MISMATCH",
                f"Aisle '{aisle.code}' declares orientation '{aisle.orientation}' "
                f"but its centerline runs along {derived_orientation}",
                [aisle_ref],
                {"declared": aisle.orientation, "derived": derived_orientation},
            )

        if aisle.widthM < MIN_AISLE_WIDTH_M:
            collector.warn(
                "AISLE_TOO_NARROW",
                f"Aisle '{aisle.code}' is {round_metric(aisle.widthM)} m wide; under "
                f"{MIN_AISLE_WIDTH_M} m is tight for a counterbalance forklift",
                [aisle_ref],
            )

        if not aisle.lanes:
            collector.warn(
                "AISLE_WITHOUT_LANES", f"Aisle '{aisle.code}' has no lanes", [aisle_ref]
            )

        aisle_length = math.hypot(aisle.centerline.deltaX, aisle.centerline.deltaZ)
        origin = (aisle.centerline.x1, aisle.centerline.z1)
        perp_left = perpendicular_left(forward)
        half_width = aisle.widthM / 2

        corridor = oriented_rect_aabb(
            origin, forward, perp_left, 0.0, aisle_length, -half_width, half_width
        )
        if not contains(footprint, corridor):
            collector.error(
                "AISLE_OUT_OF_FOOTPRINT",
                f"Aisle '{aisle.code}' extends beyond the warehouse footprint",
                [aisle_ref],
            )
        for obstacle, rect in obstacle_rects:
            if overlaps(corridor, rect):
                collector.error(
                    "AISLE_OBSTACLE_OVERLAP",
                    f"Aisle '{aisle.code}' intersects obstacle '{obstacle.label}'",
                    [
                        aisle_ref,
                        EntityRef(
                            kind="obstacle", id=obstacle.label, label=obstacle.kind
                        ),
                    ],
                )

        zone_code = doc.zone_code_for(aisle)
        zone_ordinal = zone_ordinals.get(zone_code, 1)
        zone_path = naming.wms_segment("zone", zone_ordinal, zone_code, scheme)
        aisle_path = naming.join_path(
            zone_path, naming.wms_segment("aisle", aisle_index, aisle.code, scheme)
        )

        for lane_index, lane in enumerate(aisle.lanes, start=1):
            _compile_lane(
                doc=doc,
                aisle=aisle,
                lane=lane,
                lane_index=lane_index,
                rack_types=rack_types,
                scheme=scheme,
                utilization=utilization,
                aisle_length=aisle_length,
                origin=origin,
                forward=forward,
                perp_left=perp_left,
                half_width=half_width,
                derived_orientation=derived_orientation,
                footprint=footprint,
                obstacle_rects=obstacle_rects,
                zone_code=zone_code,
                zone_path=zone_path,
                aisle_path=aisle_path,
                collector=collector,
                bays=bays,
                bins=bins,
                bay_rects=bay_rects,
                code_counts=code_counts,
                code_first_seen=code_first_seen,
            )

    # Reported after the full pass so each offending code is named once with its
    # total count, rather than once per colliding bin.
    duplicates = sorted(
        ((code, count) for code, count in code_counts.items() if count > 1),
        key=lambda item: item[0],
    )
    for code, count in duplicates:
        collector.error(
            "BIN_CODE_DUPLICATE",
            f"Bin code '{code}' is produced {count} times; the lane bin code pattern "
            "is not unique enough",
            [code_first_seen.get(code, warehouse_ref)],
            {"code": code, "count": count},
        )

    # Lanes that occupy the same floor space - catches aisles placed too close.
    for key_a, key_b in _overlapping_pairs(bay_rects):
        collector.error(
            "LANE_OVERLAP",
            f"Lanes '{key_a}' and '{key_b}' occupy overlapping floor space",
            [],
        )

    return zones, bays, bins


def _zone_ordinals(
    doc: LayoutDoc, collector: DiagnosticCollector
) -> tuple[dict[str, int], dict[str, int]]:
    """Map each declared zone code to its 1-based ordinal and aisle count."""
    ordinals: dict[str, int] = {}
    counts: dict[str, int] = {}
    used: dict[int, str] = {}

    for aisle in doc.aisles:
        zone_code = doc.zone_code_for(aisle)
        counts[zone_code] = counts.get(zone_code, 0) + 1
        if zone_code in ordinals:
            continue
        digits = naming.trailing_digits(zone_code)
        ordinal = int(digits) if digits else len(ordinals) + 1
        if ordinal in used and used[ordinal] != zone_code:
            collector.error(
                "ZONE_CODE_DUPLICATE",
                f"Zone codes '{used[ordinal]}' and '{zone_code}' would both produce "
                f"the path segment for ordinal {ordinal}",
                [],
                {"ordinal": ordinal},
            )
            ordinal = max(used) + 1
        used[ordinal] = zone_code
        ordinals[zone_code] = ordinal

    return ordinals, counts


def _compile_lane(
    *,
    doc: LayoutDoc,
    aisle: Aisle,
    lane: Lane,
    lane_index: int,
    rack_types: dict[str, RackType],
    scheme: naming.NamingScheme,
    utilization: float,
    aisle_length: float,
    origin: tuple[float, float],
    forward: tuple[float, float],
    perp_left: tuple[float, float],
    half_width: float,
    derived_orientation: str,
    footprint: AABB,
    obstacle_rects: list[tuple[Any, AABB]],
    zone_code: str,
    zone_path: str,
    aisle_path: str,
    collector: DiagnosticCollector,
    bays: list[CompiledBay],
    bins: list[CompiledBin],
    bay_rects: list[tuple[str, AABB]],
    code_counts: dict[str, int],
    code_first_seen: dict[str, EntityRef],
) -> None:
    """Derive one lane's bays and bins."""
    lane_ref = EntityRef(kind="lane", id=lane.id or lane.code, label=lane.code)

    rack_type = rack_types.get(lane.rackTypeId)
    if rack_type is None:
        collector.error(
            "LANE_UNKNOWN_RACK_TYPE",
            f"Lane '{lane.code}' references unknown rack type '{lane.rackTypeId}'",
            [lane_ref],
        )
        return

    if lane.startOffsetM + lane.lengthM > aisle_length + EPS:
        collector.error(
            "LANE_RUN_EXCEEDS_AISLE",
            f"Lane '{lane.code}' runs {round_metric(lane.startOffsetM + lane.lengthM)} m "
            f"but aisle '{aisle.code}' is only {round_metric(aisle_length)} m long",
            [
                lane_ref,
                EntityRef(kind="aisle", id=aisle.id or aisle.code, label=aisle.code),
            ],
        )

    stack_height = 0.0
    for level_index, level in enumerate(lane.levels):
        if level.binDepthM > rack_type.depthM + EPS:
            collector.warn(
                "LEVEL_DEPTH_EXCEEDS_RACK",
                f"Level {level_index + 1} of lane '{lane.code}' is "
                f"{round_metric(level.binDepthM)} m deep but rack type "
                f"'{rack_type.code}' is {round_metric(rack_type.depthM)} m deep",
                [
                    lane_ref,
                    EntityRef(
                        kind="level",
                        id=f"{lane.id or lane.code}:{level_index}",
                        label=f"L{level_index + 1:02d}",
                    ),
                ],
            )
        stack_height += level.stackHeightM

    if stack_height > doc.warehouse.heightM + EPS:
        collector.error(
            "LEVEL_STACK_EXCEEDS_HEIGHT",
            f"Lane '{lane.code}' stacks to {round_metric(stack_height)} m but the "
            f"warehouse is {round_metric(doc.warehouse.heightM)} m tall",
            [
                lane_ref,
                EntityRef(
                    kind="warehouse",
                    id=doc.warehouse.id or doc.warehouse.code,
                    label=doc.warehouse.code,
                ),
            ],
            {
                "stackHeightM": round_metric(stack_height),
                "warehouseHeightM": doc.warehouse.heightM,
            },
        )

    bay_count = floor_count(lane.lengthM, rack_type.bayWidthM)
    if bay_count == 0:
        collector.warn(
            "LANE_ZERO_BAYS",
            f"Lane '{lane.code}' is shorter than one {round_metric(rack_type.bayWidthM)} m bay",
            [lane_ref],
        )
        return

    rack_segments = [
        segment for segment in lane.resolvedSegments if segment.kind == "RACK"
    ]
    if not rack_segments:
        collector.warn(
            "LANE_HAS_NO_RACK_SEGMENT",
            f"Lane '{lane.code}' has no RACK segment, so it produces no bins",
            [lane_ref],
        )

    perp = perp_left if lane.side == "LEFT" else perpendicular_right(forward)
    lane_offset = half_width + rack_type.depthM / 2
    rotation_deg = 0 if derived_orientation == "X" else 90
    bay_path = naming.join_path(
        aisle_path, naming.wms_segment("bay", lane_index, lane.code, scheme)
    )
    # Lane identity for the overlap diagnostic. Lane codes may legitimately
    # repeat inside one aisle, so the ordinal is part of the key: sharing a key
    # would make ``_overlapping_pairs`` skip the pair as a self-comparison.
    bay_key = f"{aisle.code}/{lane.code}#{lane_index}"

    for index in range(bay_count):
        bay_seq = index + 1
        center_along = (index + 0.5) * rack_type.bayWidthM
        in_rack_run = any(
            center_along >= segment.startM - EPS and center_along <= segment.endM + EPS
            for segment in rack_segments
        )
        is_skipped = bay_seq in lane.skipBays

        offset_along = lane.startOffsetM + center_along
        cx = origin[0] + forward[0] * offset_along + perp[0] * lane_offset
        cz = origin[1] + forward[1] * offset_along + perp[1] * lane_offset

        bays.append(
            CompiledBay(
                zoneCode=zone_code,
                aisleId=aisle.id or aisle.code,
                aisleCode=aisle.code,
                laneCode=lane.code,
                side=lane.side,
                seq=bay_seq,
                isSkipped=is_skipped,
                inRackRun=in_rack_run,
                centerX=round_metric(cx),
                centerZ=round_metric(cz),
                widthM=rack_type.bayWidthM,
                depthM=rack_type.depthM,
                rotationDeg=rotation_deg,
                zonePath=zone_path,
                aislePath=aisle_path,
                path=bay_path,
                code=naming.wms_segment("bay", lane_index, lane.code, scheme),
            )
        )

        half_along = rack_type.bayWidthM / 2
        bay_rect = oriented_rect_aabb(
            origin,
            forward,
            perp,
            offset_along - half_along,
            offset_along + half_along,
            lane_offset - rack_type.depthM / 2,
            lane_offset + rack_type.depthM / 2,
        )
        bay_rects.append((bay_key, bay_rect))

        if not in_rack_run or is_skipped:
            continue

        if not contains(footprint, bay_rect):
            collector.error(
                "BIN_OUT_OF_FOOTPRINT",
                f"Bay {bay_seq} of lane '{lane.code}' extends beyond the warehouse footprint",
                [
                    lane_ref,
                    EntityRef(
                        kind="bay",
                        id=f"{lane.id or lane.code}:{bay_seq}",
                        label=f"B{bay_seq:02d}",
                    ),
                ],
            )

        for obstacle, rect in obstacle_rects:
            if overlaps(bay_rect, rect):
                collector.error(
                    "BAY_OBSTACLE_OVERLAP",
                    f"Bay {bay_seq} of lane '{lane.code}' collides with obstacle "
                    f"'{obstacle.label}'",
                    [
                        lane_ref,
                        EntityRef(
                            kind="obstacle", id=obstacle.label, label=obstacle.kind
                        ),
                    ],
                    {"baySeq": bay_seq},
                )

        height = 0.0
        for level_index, level in enumerate(lane.levels):
            bottom = height + level.beamHeightM
            center_y = bottom + level.clearHeightM / 2
            height = bottom + level.clearHeightM

            level_code = naming.wms_segment("level", level_index + 1, None, scheme)
            level_path = naming.join_path(bay_path, level_code)
            # A bin enumerates *along* the rack row, which is how the WMS
            # generator numbers bins (`BN{b:02d}` over the row's bays). The row
            # itself is the WMS `bay` location, so the document's bay number
            # becomes the bin's ordinal.
            bin_code = naming.wms_segment("bin", bay_seq, None, scheme)
            bin_path = naming.join_path(level_path, bin_code)

            label = naming.format_bin_code(
                lane.binCodePattern,
                {
                    "warehouse": doc.warehouse.code,
                    "aisle": aisle.code,
                    "lane": lane.code,
                    "side": lane.side,
                    "bay": bay_seq,
                    "level": level_index + 1,
                },
            )

            count = code_counts.get(label, 0) + 1
            code_counts[label] = count
            code_first_seen.setdefault(label, lane_ref)

            raw_volume = rack_type.bayWidthM * level.clearHeightM * level.binDepthM
            usable_volume = raw_volume * utilization

            bins.append(
                CompiledBin(
                    label=label,
                    warehouseCode=doc.warehouse.code,
                    zoneCode=zone_code,
                    aisleCode=aisle.code,
                    laneCode=lane.code,
                    side=lane.side,
                    baySeq=bay_seq,
                    levelIndex=level_index,
                    centerX=round_metric(cx),
                    centerY=round_metric(center_y),
                    centerZ=round_metric(cz),
                    widthM=rack_type.bayWidthM,
                    heightM=level.clearHeightM,
                    depthM=level.binDepthM,
                    rotationDeg=rotation_deg,
                    capacityM3=round_metric(raw_volume),
                    usableVolumeM3=round_metric(usable_volume),
                    maxVolumeCc=round_metric(usable_volume * CC_PER_M3, 2),
                    maxWeightKg=level.maxWeightKg,
                    levelPath=level_path,
                    path=bin_path,
                    code=bin_code,
                )
            )


def _overlapping_pairs(rects: list[tuple[str, AABB]]) -> list[tuple[str, str]]:
    """Lane pairs whose floor space overlaps, via a sweep on the X axis.

    Sorted by ``min_x``, so once a rectangle starts to the right of the current
    one's ``max_x`` no later rectangle can overlap it and the inner loop can stop.
    """
    ordered = sorted(rects, key=lambda item: item[1].min_x)
    pairs: set[tuple[str, str]] = set()

    for index, (key_a, rect_a) in enumerate(ordered):
        for key_b, rect_b in ordered[index + 1 :]:
            if rect_b.min_x >= rect_a.max_x - EPS:
                break
            if key_a == key_b:
                continue
            if overlap_area(rect_a, rect_b) > 0:
                pairs.add((key_a, key_b) if key_a < key_b else (key_b, key_a))

    return sorted(pairs)
