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

from sqlalchemy import String, func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.warehouse import Warehouse
from app.models.warehouse_floor_plan import WarehouseFloorPlan
from app.models.warehouse_location import WarehouseLocation
from app.schemas.floor_plan import (
    AisleSpec,
    FloorPlanApplyResponse,
    FloorPlanConfig,
    FloorPlanDeleteResponse,
    FloorPlanPreviewResponse,
    FloorPlanUpdateResponse,
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

        Always deactivates existing locations for this warehouse and marks all
        other floor plans as inactive — only one layout is active at a time.
        """
        warehouse = self._require_warehouse(warehouse_id, org_id)
        warehouse_code = warehouse.code or "WH"

        # Always deactivate existing locations (single active layout enforcement)
        deleted = self._deactivate_existing(warehouse_id, org_id)

        # Mark all existing floor plans for this warehouse as inactive
        self._deactivate_all_plans(warehouse_id, org_id)

        locations = self._build_locations(
            warehouse_id, org_id, config, warehouse_code
        )
        self._assign_bin_qr_codes(locations)
        for loc in locations:
            self.db.add(loc)

        # Save the floor plan record (active)
        now = datetime.now(UTC)
        floor_plan = WarehouseFloorPlan(
            organization_id=org_id,
            warehouse_id=warehouse_id,
            name=name,
            description=description,
            config=config.model_dump(),
            generated_at=now,
            is_active=True,
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

    def update(
        self,
        floor_plan_id: UUID,
        org_id: UUID,
        config: FloorPlanConfig,
        name: str | None = None,
        description: str | None = None,
    ) -> FloorPlanUpdateResponse:
        """Update an existing floor plan: deactivate old locations, regenerate new ones.

        The floor plan record is updated in-place (same ID preserved).
        Enforces single active layout — marks all other plans as inactive.
        """
        floor_plan = (
            self.db.query(WarehouseFloorPlan)
            .filter(
                WarehouseFloorPlan.id == floor_plan_id,
                WarehouseFloorPlan.organization_id == org_id,
            )
            .first()
        )
        if floor_plan is None:
            raise NotFoundError(
                message="Floor plan not found",
                entity_type="WarehouseFloorPlan",
                entity_id=str(floor_plan_id),
            )

        warehouse = self._require_warehouse(floor_plan.warehouse_id, org_id)
        warehouse_code = warehouse.code or "WH"

        # Deactivate all existing locations
        deleted = self._deactivate_existing(floor_plan.warehouse_id, org_id)

        # Mark all other floor plans as inactive
        self._deactivate_all_plans(floor_plan.warehouse_id, org_id)

        # Generate new locations from updated config
        locations = self._build_locations(
            floor_plan.warehouse_id, org_id, config, warehouse_code
        )
        self._assign_bin_qr_codes(locations)
        for loc in locations:
            self.db.add(loc)

        # Update the floor plan record and mark it active
        now = datetime.now(UTC)
        floor_plan.config = config.model_dump()
        floor_plan.generated_at = now
        floor_plan.is_active = True
        if name is not None:
            floor_plan.name = name
        if description is not None:
            floor_plan.description = description
        floor_plan.updated_at = now

        self.db.commit()

        summary = self._summarise(locations)
        return FloorPlanUpdateResponse(
            floor_plan_id=floor_plan.id,
            name=floor_plan.name,
            locations_created=len(locations),
            locations_deleted=deleted,
            summary=summary,
        )

    def delete(
        self,
        floor_plan_id: UUID,
        org_id: UUID,
        deactivate_locations: bool = False,
    ) -> FloorPlanDeleteResponse:
        """Soft-delete a floor plan.  Optionally deactivate its generated locations."""
        floor_plan = (
            self.db.query(WarehouseFloorPlan)
            .filter(
                WarehouseFloorPlan.id == floor_plan_id,
                WarehouseFloorPlan.organization_id == org_id,
            )
            .first()
        )
        if floor_plan is None:
            raise NotFoundError(
                message="Floor plan not found",
                entity_type="WarehouseFloorPlan",
                entity_id=str(floor_plan_id),
            )

        deactivated = 0
        if deactivate_locations:
            deactivated = self._deactivate_existing(floor_plan.warehouse_id, org_id)

        floor_plan.is_active = False
        floor_plan.updated_at = datetime.now(UTC)
        self.db.commit()

        return FloorPlanDeleteResponse(
            floor_plan_id=floor_plan.id,
            deleted=True,
            locations_deactivated=deactivated,
        )

    # ------------------------------------------------------------------
    # SEED LAYOUT TEMPLATES (for onboarding)
    # ------------------------------------------------------------------

    def seed_templates(self, warehouse_id: UUID, org_id: UUID) -> int:
        """Seed preloaded layout templates as inactive floor plans for a new warehouse.

        Called during warehouse creation so that admins/owners can see ready-made
        templates in the Layout Designer and modify/apply them.

        Templates are saved as `is_active=False` so they don't generate any
        locations until the user explicitly applies one.

        Returns the number of templates seeded.
        """
        templates = self._get_preset_templates()

        seeded = 0
        for tpl in templates:
            # Check if this template already exists (idempotent)
            exists = (
                self.db.query(WarehouseFloorPlan)
                .filter(
                    WarehouseFloorPlan.warehouse_id == warehouse_id,
                    WarehouseFloorPlan.organization_id == org_id,
                    WarehouseFloorPlan.name == tpl["name"],
                )
                .first()
            )
            if exists:
                continue

            plan = WarehouseFloorPlan(
                organization_id=org_id,
                warehouse_id=warehouse_id,
                name=tpl["name"],
                description=tpl["description"],
                config=tpl["config"],
                generated_at=None,  # Not applied yet
                is_active=False,  # Templates are inactive until user applies
            )
            self.db.add(plan)
            seeded += 1

        if seeded:
            self.db.flush()
        return seeded

    @staticmethod
    def _get_preset_templates() -> list[dict]:
        """Return the preset layout template definitions using corridor model."""
        return [
            {
                "name": "Small Warehouse",
                "description": "1 zone, 2 aisles (corridor), 5 levels, 100 bins — ideal for small stockrooms",
                "config": {
                    "grid_unit": 1.0,
                    "zones": [
                        {
                            "code": "A",
                            "name": "Main Storage",
                            "offset_x": 0,
                            "offset_y": 0,
                            "aisle_spacing": 6.5,
                            "aisles": [
                                {
                                    "code": "A01",
                                    "name": "Aisle 1",
                                    "direction": "horizontal",
                                    "position_along": 0,
                                    "position_start": 0,
                                    "corridor_width": 3.0,
                                    "rows": "right_only",
                                    "num_levels": 5,
                                    "level_height": 1.4,
                                    "bins_per_level": 1,
                                    "bin_capacity": 100,
                                    "num_bays_per_row": 10,
                                    "bay_depth": 1.8,
                                },
                                {
                                    "code": "A02",
                                    "name": "Aisle 2",
                                    "direction": "horizontal",
                                    "position_along": 0,
                                    "position_start": 0,
                                    "corridor_width": 3.0,
                                    "rows": "left_only",
                                    "num_levels": 5,
                                    "level_height": 1.4,
                                    "bins_per_level": 1,
                                    "bin_capacity": 100,
                                    "num_bays_per_row": 10,
                                    "bay_depth": 1.8,
                                },
                            ],
                        }
                    ],
                },
            },
            {
                "name": "Medium Warehouse",
                "description": "2 zones, 4 aisles (corridors), 5 levels, 400 bins — standard distribution",
                "config": {
                    "grid_unit": 1.0,
                    "zones": [
                        {
                            "code": "A",
                            "name": "Fast Movers",
                            "offset_x": 0,
                            "offset_y": 0,
                            "aisle_spacing": 6.5,
                            "aisles": [
                                {
                                    "code": "A01",
                                    "name": "Aisle 1",
                                    "direction": "horizontal",
                                    "position_along": 0,
                                    "position_start": 0,
                                    "corridor_width": 3.0,
                                    "rows": "right_only",
                                    "num_levels": 5,
                                    "level_height": 1.4,
                                    "bins_per_level": 1,
                                    "bin_capacity": 150,
                                    "num_bays_per_row": 15,
                                    "bay_depth": 1.8,
                                },
                                {
                                    "code": "A02",
                                    "name": "Aisle 2",
                                    "direction": "horizontal",
                                    "position_along": 0,
                                    "position_start": 0,
                                    "corridor_width": 3.0,
                                    "rows": "both",
                                    "num_levels": 5,
                                    "level_height": 1.4,
                                    "bins_per_level": 1,
                                    "bin_capacity": 150,
                                    "num_bays_per_row": 15,
                                    "bay_depth": 1.8,
                                },
                            ],
                        },
                        {
                            "code": "B",
                            "name": "Bulk Storage",
                            "offset_x": 0,
                            "offset_y": 50,
                            "aisle_spacing": 6.5,
                            "aisles": [
                                {
                                    "code": "B01",
                                    "name": "Aisle 3",
                                    "direction": "horizontal",
                                    "position_along": 0,
                                    "position_start": 0,
                                    "corridor_width": 4.0,
                                    "rows": "both",
                                    "num_levels": 3,
                                    "level_height": 2.0,
                                    "bins_per_level": 1,
                                    "bin_capacity": 500,
                                    "num_bays_per_row": 10,
                                    "bay_depth": 2.0,
                                },
                                {
                                    "code": "B02",
                                    "name": "Aisle 4",
                                    "direction": "horizontal",
                                    "position_along": 0,
                                    "position_start": 0,
                                    "corridor_width": 4.0,
                                    "rows": "left_only",
                                    "num_levels": 3,
                                    "level_height": 2.0,
                                    "bins_per_level": 1,
                                    "bin_capacity": 500,
                                    "num_bays_per_row": 10,
                                    "bay_depth": 2.0,
                                },
                            ],
                        },
                    ],
                },
            },
            {
                "name": "Large Warehouse",
                "description": "3 zones, 6 aisles, 5 levels, 900 bins — high-density racking",
                "config": {
                    "grid_unit": 1.0,
                    "zones": [
                        {
                            "code": "A",
                            "name": "Picking Zone",
                            "offset_x": 0,
                            "offset_y": 0,
                            "aisle_spacing": 6.5,
                            "aisles": [
                                {"code": "A01", "name": "Pick 1", "direction": "horizontal", "position_along": 0, "position_start": 0, "corridor_width": 3.0, "rows": "right_only", "num_levels": 5, "level_height": 1.4, "bins_per_level": 2, "bin_capacity": 100, "num_bays_per_row": 20, "bay_depth": 1.8},
                                {"code": "A02", "name": "Pick 2", "direction": "horizontal", "position_along": 0, "position_start": 0, "corridor_width": 3.0, "rows": "left_only", "num_levels": 5, "level_height": 1.4, "bins_per_level": 2, "bin_capacity": 100, "num_bays_per_row": 20, "bay_depth": 1.8},
                            ],
                        },
                        {
                            "code": "B",
                            "name": "Reserve Storage",
                            "offset_x": 0,
                            "offset_y": 55,
                            "aisle_spacing": 7.0,
                            "aisles": [
                                {"code": "B01", "name": "Reserve 1", "direction": "horizontal", "position_along": 0, "position_start": 0, "corridor_width": 4.0, "rows": "right_only", "num_levels": 6, "level_height": 1.4, "bins_per_level": 1, "bin_capacity": 300, "num_bays_per_row": 15, "bay_depth": 2.0},
                                {"code": "B02", "name": "Reserve 2", "direction": "horizontal", "position_along": 0, "position_start": 0, "corridor_width": 4.0, "rows": "left_only", "num_levels": 6, "level_height": 1.4, "bins_per_level": 1, "bin_capacity": 300, "num_bays_per_row": 15, "bay_depth": 2.0},
                            ],
                        },
                        {
                            "code": "C",
                            "name": "Cold Storage",
                            "offset_x": 0,
                            "offset_y": 110,
                            "aisle_spacing": 6.5,
                            "aisles": [
                                {"code": "C01", "name": "Cold 1", "direction": "horizontal", "position_along": 0, "position_start": 0, "corridor_width": 3.0, "rows": "right_only", "num_levels": 4, "level_height": 1.5, "bins_per_level": 1, "bin_capacity": 200, "num_bays_per_row": 12, "bay_depth": 1.8},
                                {"code": "C02", "name": "Cold 2", "direction": "horizontal", "position_along": 0, "position_start": 0, "corridor_width": 3.0, "rows": "left_only", "num_levels": 4, "level_height": 1.5, "bins_per_level": 1, "bin_capacity": 200, "num_bays_per_row": 12, "bay_depth": 1.8},
                            ],
                        },
                    ],
                },
            },
            {
                "name": "Cross-Dock Facility",
                "description": "2 zones (inbound/outbound), 4 aisles, 3 levels, 240 bins — transit hub",
                "config": {
                    "grid_unit": 1.0,
                    "zones": [
                        {
                            "code": "IN",
                            "name": "Inbound Staging",
                            "offset_x": 0,
                            "offset_y": 0,
                            "aisle_spacing": 6.5,
                            "aisles": [
                                {"code": "IN1", "name": "Receiving 1", "direction": "vertical", "position_along": 0, "position_start": 0, "corridor_width": 3.5, "rows": "right_only", "num_levels": 3, "level_height": 1.5, "bins_per_level": 1, "bin_capacity": 250, "num_bays_per_row": 12, "bay_depth": 1.8},
                                {"code": "IN2", "name": "Receiving 2", "direction": "vertical", "position_along": 0, "position_start": 0, "corridor_width": 3.5, "rows": "left_only", "num_levels": 3, "level_height": 1.5, "bins_per_level": 1, "bin_capacity": 250, "num_bays_per_row": 12, "bay_depth": 1.8},
                            ],
                        },
                        {
                            "code": "OUT",
                            "name": "Outbound Staging",
                            "offset_x": 30,
                            "offset_y": 0,
                            "aisle_spacing": 6.5,
                            "aisles": [
                                {"code": "OUT1", "name": "Dispatch 1", "direction": "vertical", "position_along": 0, "position_start": 0, "corridor_width": 3.5, "rows": "right_only", "num_levels": 3, "level_height": 1.5, "bins_per_level": 1, "bin_capacity": 250, "num_bays_per_row": 12, "bay_depth": 1.8},
                                {"code": "OUT2", "name": "Dispatch 2", "direction": "vertical", "position_along": 0, "position_start": 0, "corridor_width": 3.5, "rows": "left_only", "num_levels": 3, "level_height": 1.5, "bins_per_level": 1, "bin_capacity": 250, "num_bays_per_row": 12, "bay_depth": 1.8},
                            ],
                        },
                    ],
                },
            },
        ]

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
        """Return the full flat list of WarehouseLocation objects (unsaved).

        New corridor model:
        - Zone at (offset_x, offset_y, 0)
        - Aisles spaced by zone.aisle_spacing along the perpendicular axis
        - Each aisle has up to 2 bays (Left Row, Right Row) offset by corridor_width/2
        - Levels stack in Z (height) by level_height
        - Bins spread along the aisle length by bay_depth
        """
        locs: list[WarehouseLocation] = []

        for zone_spec in config.zones:
            zone_loc = self._make_loc(
                org_id=org_id,
                warehouse_id=warehouse_id,
                parent_id=None,
                location_type="zone",
                code=zone_spec.code,
                name=zone_spec.name,
                pos_x=zone_spec.offset_x,
                pos_y=zone_spec.offset_y,
                pos_z=0.0,
                capacity=None,
            )
            locs.append(zone_loc)

            num_aisles = len(zone_spec.aisles)
            for aisle_idx, aisle_spec in enumerate(zone_spec.aisles):
                # Auto-detect edge aisles: first aisle → right_only, last → left_only
                # (user can override via the rows field)
                rows = aisle_spec.rows
                if rows == "both":
                    # Auto-detect edge: first aisle has no left neighbor, last has no right
                    if num_aisles > 1 and aisle_idx == 0:
                        rows = "right_only"
                    elif num_aisles > 1 and aisle_idx == num_aisles - 1:
                        rows = "left_only"

                # Aisle center position
                if aisle_spec.direction == "horizontal":
                    # Aisle runs along X-axis, aisles stacked along Y
                    aisle_cx = zone_spec.offset_x + aisle_spec.position_start
                    aisle_cy = zone_spec.offset_y + aisle_idx * zone_spec.aisle_spacing + aisle_spec.position_along
                else:
                    # Aisle runs along Y-axis, aisles stacked along X
                    aisle_cx = zone_spec.offset_x + aisle_idx * zone_spec.aisle_spacing + aisle_spec.position_along
                    aisle_cy = zone_spec.offset_y + aisle_spec.position_start

                aisle_loc = self._make_loc(
                    org_id=org_id,
                    warehouse_id=warehouse_id,
                    parent_id=zone_loc.id,
                    location_type="aisle",
                    code=f"{zone_loc.code}-{aisle_spec.code}",
                    name=aisle_spec.name,
                    pos_x=aisle_cx,
                    pos_y=aisle_cy,
                    pos_z=0.0,
                    capacity=None,
                )
                locs.append(aisle_loc)

                locs += self._build_corridor_bays(
                    org_id, warehouse_id, aisle_loc, aisle_spec,
                    aisle_cx, aisle_cy, rows,
                )

        # Capacity is a per-bin attribute. Carry the layout's capacity UOM
        # (units vs volume) onto every bin so the warehouse roll-up is meaningful.
        for loc in locs:
            if loc.location_type == "bin":
                loc.capacity_uom = config.capacity_uom

        return locs

    def _build_corridor_bays(
        self,
        org_id: UUID,
        warehouse_id: UUID,
        aisle_loc: WarehouseLocation,
        spec: AisleSpec,
        aisle_cx: float,
        aisle_cy: float,
        rows: str,
    ) -> list[WarehouseLocation]:
        """Build left and/or right bay rows for a corridor aisle."""
        locs: list[WarehouseLocation] = []
        half_corridor = spec.corridor_width / 2.0

        # Determine which bay rows to create
        bay_sides: list[tuple[str, float]] = []
        if rows in ("both", "left_only"):
            bay_sides.append(("B01", -half_corridor))
        if rows in ("both", "right_only"):
            bay_sides.append(("B02", +half_corridor) if bay_sides else ("B01", +half_corridor))

        for side_code, offset in bay_sides:
            # Bay position: offset perpendicular to aisle direction
            if spec.direction == "horizontal":
                bay_x = aisle_cx
                bay_y = aisle_cy + offset
            else:
                bay_x = aisle_cx + offset
                bay_y = aisle_cy

            bay_loc = self._make_loc(
                org_id=org_id,
                warehouse_id=warehouse_id,
                parent_id=aisle_loc.id,
                location_type="bay",
                code=f"{aisle_loc.code}-{side_code}",
                name=None,
                pos_x=bay_x,
                pos_y=bay_y,
                pos_z=0.0,
                capacity=None,
            )
            locs.append(bay_loc)

            locs += self._build_levels_corridor(
                org_id, warehouse_id, bay_loc, spec, bay_x, bay_y,
            )

        return locs

    def _build_levels_corridor(
        self,
        org_id: UUID,
        warehouse_id: UUID,
        bay_loc: WarehouseLocation,
        spec: AisleSpec,
        bay_x: float,
        bay_y: float,
    ) -> list[WarehouseLocation]:
        """Build levels stacking in Z (height) within a bay."""
        locs: list[WarehouseLocation] = []

        for j in range(spec.num_levels):
            lz = float(j) * spec.level_height

            level_loc = self._make_loc(
                org_id=org_id,
                warehouse_id=warehouse_id,
                parent_id=bay_loc.id,
                location_type="level",
                code=f"{bay_loc.code}-L{j + 1:02d}",
                name=None,
                pos_x=bay_x,
                pos_y=bay_y,
                pos_z=lz,
                capacity=None,
            )
            locs.append(level_loc)

            locs += self._build_bins_corridor(
                org_id, warehouse_id, level_loc, spec, bay_x, bay_y, lz,
            )

        return locs

    def _build_bins_corridor(
        self,
        org_id: UUID,
        warehouse_id: UUID,
        level_loc: WarehouseLocation,
        spec: AisleSpec,
        bay_x: float,
        bay_y: float,
        lz: float,
    ) -> list[WarehouseLocation]:
        """Build bin slots along the aisle length within a level.

        Each bay position (along the aisle depth) × bins_per_level = total bins.
        Bins spread along the aisle direction by bay_depth.
        """
        locs: list[WarehouseLocation] = []

        for b in range(spec.num_bays_per_row):
            for k in range(spec.bins_per_level):
                bin_num = b * spec.bins_per_level + k + 1
                bin_code = f"{level_loc.code}-BN{bin_num:02d}"

                # Position along aisle direction
                if spec.direction == "horizontal":
                    bin_x = bay_x + float(b) * spec.bay_depth
                    bin_y = bay_y + float(k) * 0.9 if spec.bins_per_level > 1 else bay_y
                else:
                    bin_x = bay_x + float(k) * 0.9 if spec.bins_per_level > 1 else bay_x
                    bin_y = bay_y + float(b) * spec.bay_depth

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

    def _assign_bin_qr_codes(self, locations: list[WarehouseLocation]) -> None:
        """Assign a unique 5-char short code to every generated bin.

        Layout-generated bins previously had no ``qr_code`` — the 5-char code
        was only auto-generated for manually created bins (LayoutService). The
        mobile app and ``/warehouse-locations/by-qr`` lookup rely on the short
        code, so every physical bin must carry one.
        """
        import random

        from sqlalchemy import text

        bins = [loc for loc in locations if loc.location_type == "bin"]
        if not bins:
            return

        # Serialize concurrent layout generation with a transaction-scoped
        # advisory lock (per org and per warehouse). Without it, two simultaneous
        # applies both read the same "existing codes" snapshot and can pick the
        # same 5-char code, failing the unique constraint at commit with no retry.
        lock_keys = {
            f"qr:{k}"
            for k in [
                *(loc.organization_id for loc in bins if loc.organization_id),
                *(loc.warehouse_id for loc in bins if loc.warehouse_id),
            ]
        }
        for key in lock_keys:
            try:
                self.db.execute(
                    text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                    {"key": key},
                )
            except Exception:
                # Non-Postgres backends (e.g. SQLite tests) have no advisory
                # locks — degrade to the snapshot approach.
                pass

        # Load existing non-null codes once (instead of one query per bin).
        existing = {
            row[0]
            for row in self.db.query(WarehouseLocation.qr_code)
            .filter(WarehouseLocation.qr_code.isnot(None))
            .all()
        }

        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        for loc in bins:
            for _ in range(10):
                code = "".join(random.choices(chars, k=5))
                if code not in existing:
                    existing.add(code)
                    loc.qr_code = code
                    break
            else:
                raise RuntimeError(
                    "Failed to generate a unique QR code after 10 attempts"
                )

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
            full_path=code,
            name=name,
            position_x=pos_x,
            position_y=pos_y,
            position_z=pos_z,
            capacity=capacity,
            total_capacity=capacity or 0,
            available_capacity=capacity or 0,
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
        """Soft-deactivate existing *pickable* locations for this warehouse.

        Renames full_path to avoid unique-constraint collisions with
        newly generated locations, and sets is_active=False.

        Non-pickable system bins (RECEIVING-STAGE, HOLD, QUARANTINE, ...) are
        deliberately preserved — they are logical staging locations, not part of
        the physical layout, and must keep receiving stock after a layout apply.

        Previously this method hard-deleted locations without stock, but that
        caused IntegrityError when other tables (pick_list_items,
        put_away_items, bin_reservations, location_allocations) still
        referenced them via foreign keys.
        """
        from sqlalchemy import func

        # Count total active, pickable locations
        count = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
                WarehouseLocation.is_active.is_(True),
                WarehouseLocation.is_pickable.is_(True),
            )
            .count()
        )

        if count == 0:
            return 0

        # Soft-deactivate pickable locations (rename full_path + set inactive)
        # This avoids FK violations from pick_list_items, put_away_items,
        # bin_reservations, and location_allocations.
        self.db.query(WarehouseLocation).filter(
            WarehouseLocation.warehouse_id == warehouse_id,
            WarehouseLocation.organization_id == org_id,
            WarehouseLocation.is_active.is_(True),
            WarehouseLocation.is_pickable.is_(True),
        ).update(
            {
                "is_active": False,
                "full_path": func.concat(
                    "_inactive_",
                    func.cast(WarehouseLocation.id, String),
                    "_",
                    WarehouseLocation.full_path,
                ),
            },
            synchronize_session="fetch",
        )

        self.db.flush()
        return count

    def _deactivate_all_plans(
        self, warehouse_id: UUID, org_id: UUID
    ) -> None:
        """Mark all floor plans for this warehouse as inactive (single active enforcement)."""
        plans = (
            self.db.query(WarehouseFloorPlan)
            .filter(
                WarehouseFloorPlan.warehouse_id == warehouse_id,
                WarehouseFloorPlan.organization_id == org_id,
                WarehouseFloorPlan.is_active.is_(True),
            )
            .all()
        )
        for plan in plans:
            plan.is_active = False
        if plans:
            self.db.flush()

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
