"""Floor Plan Generator Service.

Converts a FloorPlanConfig (zones → aisles → bays specification) into a full
hierarchy of WarehouseLocation rows, each with correct position_x / position_y
/ position_z values that the 3D isometric renderer can use immediately.

Position assignment rules:
- Zone at (zone.grid_x, zone.grid_y, 0)
- Aisle at (zone.grid_x + aisle.grid_x, zone.grid_y + aisle.grid_y, 0)
- Bay[i]:
    orientation='x' → (aisle_x + i * bay_spacing, aisle_y, 0)
    orientation='y' → (aisle_x, aisle_y + i * bay_spacing, 0)
- Level[j]: (bay_x, bay_y, j * 1.0)
- Bin[k] (when bins_per_level > 1, spread in the perpendicular direction):
    orientation='x' → (level_x, level_y + k, level_z)
    orientation='y' → (level_x + k, level_y, level_z)

Location codes:
  Zone:  {warehouse.code}-{zone.code}          e.g. WH1-A
  Aisle: {zone_code}-{aisle.code}              e.g. WH1-A-A01
  Bay:   {aisle_code}-B{i+1:02d}              e.g. WH1-A-A01-B01
  Level: {bay_code}-L{j+1}                    e.g. WH1-A-A01-B01-L1
  Bin:   {level_code}-{k+1:02d}              e.g. WH1-A-A01-B01-L1-01
         (or just {level_code} when bins_per_level == 1)

Design ref: docs/3D_WAREHOUSE_VIEW_DESIGN.md section 2.1
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.warehouse import Warehouse
from app.models.warehouse_floor_plan import WarehouseFloorPlan
from app.models.warehouse_location import WarehouseLocation
from app.schemas.floor_plan import (
    AisleSpec,
    FloorPlanApplyResponse,
    FloorPlanConfig,
    FloorPlanPreviewResponse,
    GeneratedLocationSummary,
    ZoneSpec,
)


class FloorPlanGeneratorService:
    """Generates and persists warehouse location hierarchies from a floor plan."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def preview(
        self, warehouse_id: UUID, org_id: UUID, config: FloorPlanConfig
    ) -> FloorPlanPreviewResponse:
        """Dry-run: compute positions and return a summary (no DB writes)."""
        self._require_warehouse(warehouse_id, org_id)
        locations = self._build_locations(
            warehouse_id, org_id, config, warehouse_code="WH"
        )
        summary = self._summarise(locations)
        return FloorPlanPreviewResponse(
            warehouse_id=warehouse_id,
            summary=summary,
            config=config,
        )

    def apply(
        self,
        warehouse_id: UUID,
        org_id: UUID,
        config: FloorPlanConfig,
        name: str,
        description: str | None = None,
        replace_existing: bool = False,
    ) -> FloorPlanApplyResponse:
        """Generate locations and persist them.  Returns a summary.

        If replace_existing=True, all existing locations for this warehouse are
        soft-deleted (is_active=False) before the new ones are inserted.
        """
        warehouse = self._require_warehouse(warehouse_id, org_id)
        warehouse_code = warehouse.code or "WH"

        deleted = 0
        if replace_existing:
            deleted = self._deactivate_existing(warehouse_id, org_id)

        locations = self._build_locations(
            warehouse_id, org_id, config, warehouse_code
        )
        for loc in locations:
            self.db.add(loc)

        # Save or update the floor plan record
        now = datetime.now(UTC)
        floor_plan = WarehouseFloorPlan(
            organization_id=org_id,
            warehouse_id=warehouse_id,
            name=name,
            description=description,
            config=config.model_dump(),
            generated_at=now,
        )
        self.db.add(floor_plan)
        self.db.commit()

        summary = self._summarise(locations)
        return FloorPlanApplyResponse(
            floor_plan_id=floor_plan.id,
            locations_created=len(locations),
            locations_deleted=deleted,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # INTERNAL — HIERARCHY BUILDER
    # ------------------------------------------------------------------

    def _build_locations(
        self,
        warehouse_id: UUID,
        org_id: UUID,
        config: FloorPlanConfig,
        warehouse_code: str,
    ) -> list[WarehouseLocation]:
        """Return the full flat list of WarehouseLocation objects (unsaved)."""
        locs: list[WarehouseLocation] = []

        for zone_spec in config.zones:
            zone_loc = self._make_loc(
                org_id=org_id,
                warehouse_id=warehouse_id,
                parent_id=None,
                location_type="zone",
                code=f"{warehouse_code}-{zone_spec.code}",
                name=zone_spec.name,
                pos_x=zone_spec.grid_x,
                pos_y=zone_spec.grid_y,
                pos_z=0.0,
                capacity=None,
            )
            locs.append(zone_loc)

            for aisle_spec in zone_spec.aisles:
                aisle_loc = self._make_loc(
                    org_id=org_id,
                    warehouse_id=warehouse_id,
                    parent_id=zone_loc.id,
                    location_type="aisle",
                    code=f"{zone_loc.code}-{aisle_spec.code}",
                    name=aisle_spec.name,
                    pos_x=zone_spec.grid_x + aisle_spec.grid_x,
                    pos_y=zone_spec.grid_y + aisle_spec.grid_y,
                    pos_z=0.0,
                    capacity=None,
                )
                locs.append(aisle_loc)

                locs += self._build_bays(
                    org_id, warehouse_id, aisle_loc, aisle_spec
                )

        return locs

    def _build_bays(
        self,
        org_id: UUID,
        warehouse_id: UUID,
        aisle_loc: WarehouseLocation,
        spec: AisleSpec,
    ) -> list[WarehouseLocation]:
        locs: list[WarehouseLocation] = []
        ax, ay = aisle_loc.position_x or 0.0, aisle_loc.position_y or 0.0

        for i in range(spec.num_bays):
            if spec.orientation == "x":
                bx, by = ax + i * spec.bay_spacing, ay
            else:
                bx, by = ax, ay + i * spec.bay_spacing

            bay_loc = self._make_loc(
                org_id=org_id,
                warehouse_id=warehouse_id,
                parent_id=aisle_loc.id,
                location_type="bay",
                code=f"{aisle_loc.code}-B{i + 1:02d}",
                name=None,
                pos_x=bx,
                pos_y=by,
                pos_z=0.0,
                capacity=None,
            )
            locs.append(bay_loc)

            locs += self._build_levels(
                org_id, warehouse_id, bay_loc, spec, bx, by
            )

        return locs

    def _build_levels(
        self,
        org_id: UUID,
        warehouse_id: UUID,
        bay_loc: WarehouseLocation,
        spec: AisleSpec,
        bx: float,
        by: float,
    ) -> list[WarehouseLocation]:
        locs: list[WarehouseLocation] = []

        for j in range(spec.num_levels):
            lz = float(j)
            level_loc = self._make_loc(
                org_id=org_id,
                warehouse_id=warehouse_id,
                parent_id=bay_loc.id,
                location_type="level",
                code=f"{bay_loc.code}-L{j + 1}",
                name=None,
                pos_x=bx,
                pos_y=by,
                pos_z=lz,
                capacity=None,
            )
            locs.append(level_loc)

            locs += self._build_bins(
                org_id, warehouse_id, level_loc, spec, bx, by, lz
            )

        return locs

    def _build_bins(
        self,
        org_id: UUID,
        warehouse_id: UUID,
        level_loc: WarehouseLocation,
        spec: AisleSpec,
        bx: float,
        by: float,
        lz: float,
    ) -> list[WarehouseLocation]:
        locs: list[WarehouseLocation] = []

        for k in range(spec.bins_per_level):
            if spec.bins_per_level == 1:
                bin_code = level_loc.code
            else:
                bin_code = f"{level_loc.code}-{k + 1:02d}"

            if spec.orientation == "x":
                bin_x, bin_y = bx, by + float(k)
            else:
                bin_x, bin_y = bx + float(k), by

            bin_loc = self._make_loc(
                org_id=org_id,
                warehouse_id=warehouse_id,
                parent_id=level_loc.id,
                location_type="bin",
                code=bin_code,
                name=None,
                pos_x=bin_x,
                pos_y=bin_y,
                pos_z=lz,
                capacity=spec.bin_capacity,
            )
            locs.append(bin_loc)

        return locs

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _make_loc(
        org_id: UUID,
        warehouse_id: UUID,
        parent_id: UUID | None,
        location_type: str,
        code: str,
        name: str | None,
        pos_x: float,
        pos_y: float,
        pos_z: float,
        capacity: float | None,
    ) -> WarehouseLocation:
        return WarehouseLocation(
            id=uuid4(),
            organization_id=org_id,
            warehouse_id=warehouse_id,
            parent_location_id=parent_id,
            location_type=location_type,
            code=code,
            name=name,
            position_x=pos_x,
            position_y=pos_y,
            position_z=pos_z,
            capacity=capacity,
            is_active=True,
        )

    def _require_warehouse(
        self, warehouse_id: UUID, org_id: UUID
    ) -> Warehouse:
        wh = (
            self.db.query(Warehouse)
            .filter(
                Warehouse.id == warehouse_id,
                Warehouse.organization_id == org_id,
            )
            .first()
        )
        if wh is None:
            raise NotFoundError(
                message="Warehouse not found",
                entity_type="Warehouse",
                entity_id=str(warehouse_id),
            )
        return wh

    def _deactivate_existing(
        self, warehouse_id: UUID, org_id: UUID
    ) -> int:
        rows = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
                WarehouseLocation.is_active.is_(True),
            )
            .all()
        )
        for loc in rows:
            loc.is_active = False
        if rows:
            self.db.flush()
        return len(rows)

    @staticmethod
    def _summarise(locations: list[WarehouseLocation]) -> GeneratedLocationSummary:
        bins = [l for l in locations if l.location_type == "bin"]
        sample = [b.code for b in bins[:6]]
        return GeneratedLocationSummary(
            zone_count=sum(1 for l in locations if l.location_type == "zone"),
            aisle_count=sum(1 for l in locations if l.location_type == "aisle"),
            bay_count=sum(1 for l in locations if l.location_type == "bay"),
            level_count=sum(1 for l in locations if l.location_type == "level"),
            bin_count=len(bins),
            sample_bin_codes=sample,
        )
