"""Materialise a compiled layout into ``WarehouseLocation`` rows.

Pure with respect to the database: it builds (but never adds or commits) ORM
objects, applies the WMS naming scheme, and reports conflicts with locations that
already exist. The service layer owns the session.

Hierarchy written, one row per level of the WMS tree::

    zone   Z01                        position (origin, 0)
    aisle  Z01-A01                    position (centerline start, 0)
    bay    Z01-A01-B01                position (rack row centre, 0)   <- a LANE
    level  Z01-A01-B01-L01            position (row centre, level centre height)
    bin    Z01-A01-B01-L01-BN001      position (bay centre, level centre height)

Note the two senses of "bay": the document's bay is a *position along a rack row*,
and it becomes a **bin** here, enumerated along the row. The WMS ``bay`` location
is the **rack row** itself, which is how ``FloorPlanGeneratorService`` assigns its
``B01``/``B02`` side codes. That mapping is what keeps the document's bin count
equal to the WMS bin count.

Identifiers are assigned explicitly (``uuid4()``) so parents can be linked without
a per-row flush.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md section 4
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.layout_design import naming
from app.layout_design.compile import CompiledBin, CompiledLayout, Diagnostic, EntityRef
from app.layout_design.geometry import (
    EPS,
    normalize2,
    perpendicular_left,
    perpendicular_right,
)
from app.layout_design.naming import NamingScheme
from app.layout_design.rules import LOCATION_PATH_ALREADY_EXISTS
from app.models.warehouse_location import WarehouseLocation

#: ``WarehouseLocation.capacity_uom`` value for physically-limited bins.
VOLUME_UOM = "volume"


def _dec(value: float, scale: int = 2) -> Decimal:
    """Decimal rounded to the column's scale (positions are Numeric(10,2))."""
    return Decimal(str(round(value, scale)))


@dataclass
class MaterializedLayout:
    """The rows a document would write, plus any path conflicts."""

    rows: list[WarehouseLocation] = field(default_factory=list)
    zone_count: int = 0
    aisle_count: int = 0
    bay_count: int = 0
    level_count: int = 0
    bin_count: int = 0
    conflicts: list[Diagnostic] = field(default_factory=list)

    @property
    def location_count(self) -> int:
        return len(self.rows)

    def counts(self) -> dict[str, int]:
        """Row counts by location type, for an apply response."""
        return {
            "zones": self.zone_count,
            "aisles": self.aisle_count,
            "bays": self.bay_count,
            "levels": self.level_count,
            "bins": self.bin_count,
            "locations": self.location_count,
        }


def materialize_layout(
    compiled: CompiledLayout,
    *,
    organization_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    qr_codes: list[str] | None = None,
    existing_paths: dict[str, str] | None = None,
) -> MaterializedLayout:
    """Build the location rows for a compiled document.

    Args:
        compiled: A successful compile (``compiled.doc`` and ``compiled.applyable``
            must hold; the caller guards this).
        organization_id: Owning organisation, from the authenticated user.
        warehouse_id: Target warehouse UUID.
        qr_codes: Pre-generated QR codes for the bins, in bin order. Generated
            in one batch by the service so a QP has no per-bin query.
        existing_paths: ``{full_path: location_type}`` for the warehouse, so a
            path collision with an incompatible type can be reported instead of
            silently overwriting a zone with a bin.

    Returns:
        The rows plus any ``LOCATION_PATH_ALREADY_EXISTS`` conflicts found. A
        conflict is reported, not raised: the caller decides whether to abort.
    """
    doc = compiled.doc
    result = MaterializedLayout()
    if doc is None or not compiled.applyable:
        return result

    existing = existing_paths or {}
    scheme: NamingScheme = doc.layout.namingScheme
    warehouse = doc.warehouse
    by_path: dict[str, WarehouseLocation] = {}
    # Indexed once, so the per-level loop below is O(levels + bins) rather than
    # O(levels x bins) - the latter is fatal at the 100k-bin target.
    bins_by_level: dict[str, list[CompiledBin]] = {}
    for compiled_bin in compiled.bins:
        bins_by_level.setdefault(compiled_bin.levelPath, []).append(compiled_bin)
    bin_index = 0

    def _payload(path: str, location_type: str, ref: EntityRef) -> bool:
        """Register a new path, returning False when it conflicts."""
        if by_path.get(path) is not None:
            return True
        found = existing.get(path)
        if found is not None and found != location_type:
            result.conflicts.append(
                Diagnostic(
                    code=LOCATION_PATH_ALREADY_EXISTS.code,
                    severity=LOCATION_PATH_ALREADY_EXISTS.severity,
                    message=(
                        f"Location '{path}' already exists as a '{found}' but the "
                        f"document generates a '{location_type}' at that path"
                    ),
                    entityRefs=(ref,),
                    data={
                        "path": path,
                        "existingType": found,
                        "generatedType": location_type,
                    },
                )
            )
            return False
        return True

    def _new(
        *,
        location_type: str,
        code: str,
        full_path: str,
        parent: WarehouseLocation | None,
        position: tuple[float, float, float],
    ) -> WarehouseLocation:
        return WarehouseLocation(
            id=uuid.uuid4(),
            organization_id=organization_id,
            warehouse_id=warehouse_id,
            parent_location_id=parent.id if parent is not None else None,
            location_type=location_type,
            code=code,
            full_path=full_path,
            position_x=_dec(position[0]),
            position_y=_dec(position[1]),
            position_z=_dec(position[2]),
            is_active=True,
            is_available=True,
            is_pickable=True,
            version=1,
        )

    origin_x, origin_z = warehouse.origin.x, warehouse.origin.z

    # --- Zones ---------------------------------------------------------------
    zone_rows: dict[str, WarehouseLocation] = {}
    for zone in compiled.zones:
        ref = EntityRef(kind="zone", id=zone.code, label=zone.path)
        if not _payload(zone.path, "zone", ref):
            continue
        row = _new(
            location_type="zone",
            code=zone.path,
            full_path=zone.path,
            parent=None,
            position=(origin_x, origin_z, 0.0),
        )
        zone_rows[zone.code] = row
        by_path[zone.path] = row
        result.rows.append(row)
        result.zone_count += 1

    # --- Aisles, bays (rack rows), levels, bins ------------------------------
    for aisle_index, aisle in enumerate(doc.aisles, start=1):
        forward = normalize2(aisle.centerline.deltaX, aisle.centerline.deltaZ)
        if forward is None:
            continue  # compiled already reported AISLE_ZERO_LENGTH

        zone_code = doc.zone_code_for(aisle)
        zone_row = zone_rows.get(zone_code)
        if zone_row is None:
            continue

        zone_path = zone_row.full_path or zone_row.code
        aisle_code = naming.wms_segment("aisle", aisle_index, aisle.code, scheme)
        aisle_path = naming.join_path(zone_path, aisle_code)
        aisle_ref = EntityRef(kind="aisle", id=aisle.id or aisle.code, label=aisle.code)
        if not _payload(aisle_path, "aisle", aisle_ref):
            continue

        aisle_row = _new(
            location_type="aisle",
            code=aisle_code,
            full_path=aisle_path,
            parent=zone_row,
            position=(aisle.centerline.x1, aisle.centerline.z1, 0.0),
        )
        by_path[aisle_path] = aisle_row
        result.rows.append(aisle_row)
        result.aisle_count += 1

        perp_left = perpendicular_left(forward)
        half_width = aisle.widthM / 2

        for lane_index, lane in enumerate(aisle.lanes, start=1):
            rack_type = doc.rack_type_by_id.get(lane.rackTypeId)
            if rack_type is None:
                continue  # compiled already reported LANE_UNKNOWN_RACK_TYPE

            bay_code = naming.wms_segment("bay", lane_index, lane.code, scheme)
            bay_path = naming.join_path(aisle_path, bay_code)
            lane_ref = EntityRef(kind="lane", id=lane.id or lane.code, label=lane.code)
            if not _payload(bay_path, "bay", lane_ref):
                continue

            # The rack row's centre: half way along the run, offset by the
            # corridor half-width plus half the rack depth.
            perp = perp_left if lane.side == "LEFT" else perpendicular_right(forward)
            offset_along = lane.startOffsetM + lane.lengthM / 2
            lane_offset = half_width + rack_type.depthM / 2
            row_x = (
                aisle.centerline.x1 + forward[0] * offset_along + perp[0] * lane_offset
            )
            row_z = (
                aisle.centerline.z1 + forward[1] * offset_along + perp[1] * lane_offset
            )

            bay_row = _new(
                location_type="bay",
                code=bay_code,
                full_path=bay_path,
                parent=aisle_row,
                position=(row_x, row_z, 0.0),
            )
            by_path[bay_path] = bay_row
            result.rows.append(bay_row)
            result.bay_count += 1

            height = 0.0
            for level_index, level in enumerate(lane.levels):
                bottom = height + level.beamHeightM
                center_height = bottom + level.clearHeightM / 2
                height = bottom + level.clearHeightM

                level_code = naming.wms_segment("level", level_index + 1, None, scheme)
                level_path = naming.join_path(bay_path, level_code)
                level_ref = EntityRef(
                    kind="level",
                    id=f"{lane.id or lane.code}:{level_index}",
                    label=level_code,
                )
                if not _payload(level_path, "level", level_ref):
                    continue

                level_row = _new(
                    location_type="level",
                    code=level_code,
                    full_path=level_path,
                    parent=bay_row,
                    position=(row_x, row_z, center_height),
                )
                by_path[level_path] = level_row
                result.rows.append(level_row)
                result.level_count += 1

                # Every bin of this level belongs to this row, in document order.
                for compiled_bin in bins_by_level.get(level_path, ()):
                    bin_ref = EntityRef(
                        kind="bin", id=compiled_bin.path, label=compiled_bin.path
                    )
                    if not _payload(compiled_bin.path, "bin", bin_ref):
                        continue
                    bin_row = _new(
                        location_type="bin",
                        code=compiled_bin.code,
                        full_path=compiled_bin.path,
                        parent=level_row,
                        position=(
                            compiled_bin.centerX,
                            compiled_bin.centerZ,
                            compiled_bin.centerY,
                        ),
                    )
                    bin_row.capacity_uom = VOLUME_UOM
                    # `capacity` must carry the usable volume in m³: the
                    # warehouse total is a roll-up of `SUM(bin.capacity)` and
                    # `capacity_math` reads a volume-uom `capacity` as m³. Leaving
                    # it at the column default made every bin (and therefore the
                    # warehouse) report a capacity of 0.
                    volume_m3 = _dec(compiled_bin.usableVolumeM3, 3)
                    bin_row.capacity = volume_m3
                    bin_row.total_capacity = volume_m3
                    bin_row.available_capacity = volume_m3
                    bin_row.max_volume_cc = _dec(compiled_bin.maxVolumeCc)
                    if compiled_bin.maxWeightKg is not None:
                        bin_row.max_weight_grams = _dec(compiled_bin.maxWeightKg * 1000)
                    if qr_codes is not None and bin_index < len(qr_codes):
                        bin_row.qr_code = qr_codes[bin_index]
                    bin_index += 1
                    by_path[compiled_bin.path] = bin_row
                    result.rows.append(bin_row)
                    result.bin_count += 1

    return result


def count_active_bins(compiled: CompiledLayout) -> int:
    """How many bins a document yields, without materialising any row."""
    return len(compiled.bins)


def aisle_centrelines(
    compiled: CompiledLayout,
) -> list[tuple[float, float, float, float]]:
    """``(x1, z1, x2, z2)`` for each aisle, for a 2D plan overlay."""
    doc = compiled.doc
    if doc is None:
        return []
    return [
        (
            aisle.centerline.x1,
            aisle.centerline.z1,
            aisle.centerline.x2,
            aisle.centerline.z2,
        )
        for aisle in doc.aisles
        if math.hypot(aisle.centerline.deltaX, aisle.centerline.deltaZ) > EPS
    ]


def obstacle_boxes(compiled: CompiledLayout) -> list[dict[str, Any]]:
    """Obstacles as plain dicts, for the 3D/plan overlay."""
    doc = compiled.doc
    if doc is None:
        return []
    return [
        {
            "id": obstacle.label,
            "kind": obstacle.kind,
            "x": obstacle.x,
            "z": obstacle.z,
            "widthM": obstacle.widthM,
            "depthM": obstacle.depthM,
            "heightM": obstacle.heightM,
        }
        for obstacle in doc.obstacles
    ]
