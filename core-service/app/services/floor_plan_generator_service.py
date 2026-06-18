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
        """Return the preset layout template definitions."""
        return [
            {
                "name": "Small Warehouse",
                "description": "1 zone, 2 aisles, 24 bins — ideal for small stockrooms",
                "config": {
                    "grid_unit": 1.0,
                    "zones": [
                        {
                            "code": "A",
                            "name": "Main Storage",
                            "grid_x": 0,
                            "grid_y": 0,
                            "aisles": [
                                {
                                    "code": "A01",
                                    "name": "Aisle 1",
                                    "orientation": "x",
                                    "grid_x": 0,
                                    "grid_y": 0,
                                    "num_bays": 4,
                                    "bay_spacing": 1.5,
                                    "num_levels": 3,
                                    "bins_per_level": 1,
                                    "bin_capacity": 100,
                                },
                                {
                                    "code": "A02",
                                    "name": "Aisle 2",
                                    "orientation": "x",
                                    "grid_x": 0,
                                    "grid_y": 3,
                                    "num_bays": 4,
                                    "bay_spacing": 1.5,
                                    "num_levels": 3,
                                    "bins_per_level": 1,
                                    "bin_capacity": 100,
                                },
                            ],
                        }
                    ],
                },
            },
            {
                "name": "Medium Warehouse",
                "description": "2 zones, 4 aisles, 96 bins — standard distribution center",
                "config": {
                    "grid_unit": 1.0,
                    "zones": [
                        {
                            "code": "A",
                            "name": "Fast Movers",
                            "grid_x": 0,
                            "grid_y": 0,
                            "aisles": [
                                {
                                    "code": "A01",
                                    "name": "Aisle 1",
                                    "orientation": "x",
                                    "grid_x": 0,
                                    "grid_y": 0,
                                    "num_bays": 6,
                                    "bay_spacing": 1.5,
                                    "num_levels": 4,
                                    "bins_per_level": 1,
                                    "bin_capacity": 150,
                                },
                                {
                                    "code": "A02",
                                    "name": "Aisle 2",
                                    "orientation": "x",
                                    "grid_x": 0,
                                    "grid_y": 3,
                                    "num_bays": 6,
                                    "bay_spacing": 1.5,
                                    "num_levels": 4,
                                    "bins_per_level": 1,
                                    "bin_capacity": 150,
                                },
                            ],
                        },
                        {
                            "code": "B",
                            "name": "Bulk Storage",
                            "grid_x": 0,
                            "grid_y": 10,
                            "aisles": [
                                {
                                    "code": "B01",
                                    "name": "Aisle 3",
                                    "orientation": "x",
                                    "grid_x": 0,
                                    "grid_y": 0,
                                    "num_bays": 6,
                                    "bay_spacing": 1.5,
                                    "num_levels": 2,
                                    "bins_per_level": 1,
                                    "bin_capacity": 500,
                                },
                                {
                                    "code": "B02",
                                    "name": "Aisle 4",
                                    "orientation": "x",
                                    "grid_x": 0,
                                    "grid_y": 3,
                                    "num_bays": 6,
                                    "bay_spacing": 1.5,
                                    "num_levels": 2,
                                    "bins_per_level": 1,
                                    "bin_capacity": 500,
                                },
                            ],
                        },
                    ],
                },
            },
            {
                "name": "Large Warehouse",
                "description": "3 zones, 6 aisles, 216 bins — high-density racking layout",
                "config": {
                    "grid_unit": 1.0,
                    "zones": [
                        {
                            "code": "A",
                            "name": "Picking Zone",
                            "grid_x": 0,
                            "grid_y": 0,
                            "aisles": [
                                {
                                    "code": "A01",
                                    "name": "Pick Aisle 1",
                                    "orientation": "x",
                                    "grid_x": 0,
                                    "grid_y": 0,
                                    "num_bays": 8,
                                    "bay_spacing": 1.5,
                                    "num_levels": 4,
                                    "bins_per_level": 2,
                                    "bin_capacity": 100,
                                },
                                {
                                    "code": "A02",
                                    "name": "Pick Aisle 2",
                                    "orientation": "x",
                                    "grid_x": 0,
                                    "grid_y": 4,
                                    "num_bays": 8,
                                    "bay_spacing": 1.5,
                                    "num_levels": 4,
                                    "bins_per_level": 2,
                                    "bin_capacity": 100,
                                },
                            ],
                        },
                        {
                            "code": "B",
                            "name": "Reserve Storage",
                            "grid_x": 0,
                            "grid_y": 12,
                            "aisles": [
                                {
                                    "code": "B01",
                                    "name": "Reserve 1",
                                    "orientation": "y",
                                    "grid_x": 0,
                                    "grid_y": 0,
                                    "num_bays": 6,
                                    "bay_spacing": 2.0,
                                    "num_levels": 5,
                                    "bins_per_level": 1,
                                    "bin_capacity": 300,
                                },
                                {
                                    "code": "B02",
                                    "name": "Reserve 2",
                                    "orientation": "y",
                                    "grid_x": 4,
                                    "grid_y": 0,
                                    "num_bays": 6,
                                    "bay_spacing": 2.0,
                                    "num_levels": 5,
                                    "bins_per_level": 1,
                                    "bin_capacity": 300,
                                },
                            ],
                        },
                        {
                            "code": "C",
                            "name": "Cold Storage",
                            "grid_x": 0,
                            "grid_y": 26,
                            "aisles": [
                                {
                                    "code": "C01",
                                    "name": "Cold Aisle 1",
                                    "orientation": "x",
                                    "grid_x": 0,
                                    "grid_y": 0,
                                    "num_bays": 4,
                                    "bay_spacing": 2.0,
                                    "num_levels": 3,
                                    "bins_per_level": 1,
                                    "bin_capacity": 200,
                                },
                                {
                                    "code": "C02",
                                    "name": "Cold Aisle 2",
                                    "orientation": "x",
                                    "grid_x": 0,
                                    "grid_y": 4,
                                    "num_bays": 4,
                                    "bay_spacing": 2.0,
                                    "num_levels": 3,
                                    "bins_per_level": 1,
                                    "bin_capacity": 200,
                                },
                            ],
                        },
                    ],
                },
            },
            {
                "name": "Cross-Dock Facility",
                "description": "2 zones (inbound/outbound), 4 aisles, 48 bins — transit hub",
                "config": {
                    "grid_unit": 1.0,
                    "zones": [
                        {
                            "code": "IN",
                            "name": "Inbound Staging",
                            "grid_x": 0,
                            "grid_y": 0,
                            "aisles": [
                                {
                                    "code": "IN1",
                                    "name": "Receiving 1",
                                    "orientation": "y",
                                    "grid_x": 0,
                                    "grid_y": 0,
                                    "num_bays": 6,
                                    "bay_spacing": 1.5,
                                    "num_levels": 2,
                                    "bins_per_level": 1,
                                    "bin_capacity": 250,
                                },
                                {
                                    "code": "IN2",
                                    "name": "Receiving 2",
                                    "orientation": "y",
                                    "grid_x": 3,
                                    "grid_y": 0,
                                    "num_bays": 6,
                                    "bay_spacing": 1.5,
                                    "num_levels": 2,
                                    "bins_per_level": 1,
                                    "bin_capacity": 250,
                                },
                            ],
                        },
                        {
                            "code": "OUT",
                            "name": "Outbound Staging",
                            "grid_x": 10,
                            "grid_y": 0,
                            "aisles": [
                                {
                                    "code": "OUT1",
                                    "name": "Dispatch 1",
                                    "orientation": "y",
                                    "grid_x": 0,
                                    "grid_y": 0,
                                    "num_bays": 6,
                                    "bay_spacing": 1.5,
                                    "num_levels": 2,
                                    "bins_per_level": 1,
                                    "bin_capacity": 250,
                                },
                                {
                                    "code": "OUT2",
                                    "name": "Dispatch 2",
                                    "orientation": "y",
                                    "grid_x": 3,
                                    "grid_y": 0,
                                    "num_bays": 6,
                                    "bay_spacing": 1.5,
                                    "num_levels": 2,
                                    "bins_per_level": 1,
                                    "bin_capacity": 250,
                                },
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
                bin_code = f"{level_loc.code}-01"
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
            full_path=code,
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
        """Remove existing active locations for this warehouse.

        Hard-deletes locations that have no stock, soft-deletes (is_active=False)
        locations that still have stock references to preserve audit trail.
        This avoids unique constraint conflicts on (warehouse_id, full_path)
        when re-applying a layout with the same codes.
        """
        rows = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
                WarehouseLocation.is_active.is_(True),
            )
            .all()
        )
        count = len(rows)

        # Check which bins have stock — those get soft-deleted, the rest get hard-deleted
        from app.models.bin_stock_level import BinStockLevel

        bins_with_stock = set()
        if rows:
            stock_rows = (
                self.db.query(BinStockLevel.bin_location_id)
                .filter(
                    BinStockLevel.bin_location_id.in_([r.id for r in rows]),
                    BinStockLevel.quantity_on_hand > 0,
                )
                .distinct()
                .all()
            )
            bins_with_stock = {r[0] for r in stock_rows}

        for loc in rows:
            if loc.id in bins_with_stock:
                # Soft-delete — preserve for stock audit trail
                loc.is_active = False
                loc.full_path = f"_inactive_{loc.id}_{loc.full_path or loc.code}"
            else:
                # Hard-delete — no stock, safe to remove (avoids unique constraint conflict)
                self.db.delete(loc)

        if rows:
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
