"""Layout design service — compile, preview and apply JSON layout documents.

Orchestration only: the geometry lives in :mod:`app.layout_design.compile` and
the row building in :mod:`app.layout_design.materialize`, both of which are pure.
This service owns the session, the warehouse lookup, the upsert reconciliation
and the floor-plan record.

Upsert rule: a location is matched by ``full_path``. A matching path and type is
**updated in place** (its ``id`` is preserved, so placements and bin stock keep
pointing at the same bin); a path that is absent is inserted; a path that exists
with a different type is refused. Nothing is ever delete-and-recreated.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md sections 4 and 6
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.redis_pubsub import publish_layout_event
from app.layout_design.compile import CompiledLayout, Diagnostic, build_layout
from app.layout_design.examples import EXAMPLE_DOCUMENTS
from app.layout_design.materialize import MaterializedLayout, materialize_layout
from app.layout_design.naming import generate_qr_codes
from app.layout_design.rules import rule_registry_payload
from app.models.warehouse import Warehouse
from app.models.warehouse_floor_plan import WarehouseFloorPlan
from app.models.warehouse_location import WarehouseLocation
from app.schemas.layout_design import (
    LayoutAislePlanOut,
    LayoutApplyResponse,
    LayoutBinOut,
    LayoutDiagnosticOut,
    LayoutEntityRefOut,
    LayoutObstacleOut,
    LayoutPlanOut,
    LayoutPreviewResponse,
    LayoutSummaryOut,
    LayoutValidateResponse,
    LayoutZoneOut,
)

#: How many candidate QR codes to check per round trip.
QR_CHECK_BATCH = 500

#: Rounds of "generate, check, regenerate the collisions".
QR_RETRY_ROUNDS = 3

#: ``WarehouseFloorPlan.config`` source marker for JSON-imported layouts.
CONFIG_SOURCE = "json_import"


@dataclass
class LayoutApplyResult:
    """The outcome of an apply, including the refusal path.

    A refused apply is a normal result rather than an exception: the endpoint
    turns it into a 400 whose envelope ``code`` is the blocking rule code, so the
    UI can explain exactly which rule stopped it.
    """

    applyable: bool
    blocking_code: str | None = None
    diagnostics: list[LayoutDiagnosticOut] = field(default_factory=list)
    response: LayoutApplyResponse | None = None


class LayoutDesignService:
    """Service for compiling and persisting JSON layout documents."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ reads

    def list_rules(self) -> list[dict[str, str]]:
        """The diagnostic rule registry, so the UI can explain every code."""
        return rule_registry_payload()

    def list_examples(self) -> dict[str, dict[str, Any]]:
        """Import templates keyed by name."""
        return EXAMPLE_DOCUMENTS

    def get_stored_document(
        self, floor_plan_id: uuid.UUID, organization_id: uuid.UUID
    ) -> dict[str, Any] | None:
        """The layout document stored on a floor plan, or ``None``.

        Raises:
            NotFoundError: If the plan does not exist in this organisation.
        """
        plan = self._get_plan(floor_plan_id, organization_id)
        if isinstance(plan.layout_doc, dict):
            return plan.layout_doc
        # Documents applied before the `layout_doc` column existed live in `config`.
        config = plan.config or {}
        document = config.get("layout_doc")
        return document if isinstance(document, dict) else None

    # --------------------------------------------------------------- compiling

    def validate(self, document: dict[str, Any]) -> LayoutValidateResponse:
        """Compile a document and describe the result. Writes nothing."""
        compiled = build_layout(document)
        return self._validate_payload(compiled)

    def preview(
        self, document: dict[str, Any], limit: int = 25
    ) -> LayoutPreviewResponse:
        """Compile a document and return enough geometry to draw it. Writes nothing."""
        compiled = build_layout(document)
        base = self._validate_payload(compiled)

        return LayoutPreviewResponse(
            valid=base.valid,
            applyable=base.applyable,
            summary=base.summary,
            diagnostics=base.diagnostics,
            sample_bin_paths=base.sample_bin_paths,
            zones=[self._zone_out(zone) for zone in compiled.zones],
            bins=[self._bin_out(bin_) for bin_ in compiled.bins[:limit]],
            plan=self._plan_out(compiled),
        )

    # -------------------------------------------------------------- persisting

    def apply(
        self,
        *,
        warehouse_id: uuid.UUID,
        organization_id: uuid.UUID,
        document: dict[str, Any],
        name: str,
        description: str | None = None,
        replace_existing: bool = False,
    ) -> LayoutApplyResult:
        """Compile, materialise and persist a layout document.

        Raises:
            NotFoundError: If the warehouse does not exist in this organisation.
        """
        compiled = build_layout(document)
        if not compiled.applyable:
            return LayoutApplyResult(
                applyable=False,
                blocking_code=self._blocking_code(compiled),
                diagnostics=self._diagnostics_out(compiled),
            )

        warehouse = self._get_warehouse(warehouse_id, organization_id)

        existing_rows = {
            row.full_path: row
            for row in self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse.id,
                WarehouseLocation.organization_id == organization_id,
            )
            .all()
        }
        existing_types = {
            path: row.location_type for path, row in existing_rows.items() if path
        }

        desired = materialize_layout(
            compiled,
            organization_id=organization_id,
            warehouse_id=warehouse.id,
            qr_codes=self._reserve_qr_codes(len(compiled.bins)),
            existing_paths=existing_types,
        )
        if desired.conflicts:
            return LayoutApplyResult(
                applyable=False,
                blocking_code=desired.conflicts[0].code,
                diagnostics=[self._diagnostic_out(item) for item in desired.conflicts],
            )

        if replace_existing:
            self._deactivate_other_plans(warehouse.id, organization_id)

        created, updated = self._reconcile(desired, existing_rows)

        deactivated = 0
        if replace_existing:
            deactivated = self._deactivate_stale_locations(
                [row for row in desired.rows if row.full_path], existing_rows
            )

        plan = WarehouseFloorPlan(
            id=uuid.uuid4(),
            organization_id=organization_id,
            warehouse_id=warehouse.id,
            name=name,
            description=description,
            config={
                "source": CONFIG_SOURCE,
                "naming_scheme": compiled.doc.layout.namingScheme
                if compiled.doc
                else None,
                "layout_doc_summary": compiled.summary(),
            },
            layout_doc=document,
            generated_at=datetime.now(UTC),
            is_active=True,
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)

        # Published after the commit so a subscriber never refetches against an
        # uncommitted layout. Non-critical: the publisher swallows Redis errors.
        publish_layout_event(
            warehouse.id,
            bins=len(compiled.bins),
            bays=len(compiled.bays),
            floor_plan_id=plan.id,
        )

        return LayoutApplyResult(
            applyable=True,
            response=LayoutApplyResponse(
                floor_plan_id=plan.id,
                locations_created=created,
                locations_updated=updated,
                locations_deactivated=deactivated,
                summary=self._summary_out(compiled),
                sample_bin_paths=compiled.sampleBinPaths(8),
            ),
        )

    # ------------------------------------------------------------ persistence

    def _reconcile(
        self,
        desired: MaterializedLayout,
        existing_rows: dict[str, WarehouseLocation],
    ) -> tuple[int, int]:
        """Upsert the desired rows, preserving the ids of re-used locations.

        Rows arrive parents-first, so a parent's final id is known before its
        children are linked.
        """
        id_map: dict[uuid.UUID, uuid.UUID] = {}
        created = 0
        updated = 0

        for row in desired.rows:
            parent_desired_id = row.parent_location_id
            actual_parent_id = (
                id_map.get(parent_desired_id) if parent_desired_id else None
            )

            current = existing_rows.get(row.full_path or "")
            if current is not None and current.location_type == row.location_type:
                self._adopt(current, row)
                current.parent_location_id = actual_parent_id
                current.is_active = True
                id_map[row.id] = current.id
                updated += 1
                continue

            row.parent_location_id = actual_parent_id
            self.db.add(row)
            id_map[row.id] = row.id
            created += 1

        return created, updated

    @staticmethod
    def _adopt(current: WarehouseLocation, desired: WarehouseLocation) -> None:
        """Copy the generated fields onto a location that already exists in place."""
        current.code = desired.code
        current.full_path = desired.full_path
        current.position_x = desired.position_x
        current.position_y = desired.position_y
        current.position_z = desired.position_z
        current.capacity_uom = desired.capacity_uom
        current.max_volume_cc = desired.max_volume_cc
        current.max_weight_grams = desired.max_weight_grams
        current.is_pickable = desired.is_pickable
        if desired.qr_code and not current.qr_code:
            current.qr_code = desired.qr_code
        # Bump the optimistic-lock token, since this is a real modification that
        # a concurrent BinCapacityService write must not clobber.
        current.version = (current.version or 1) + 1

    def _deactivate_stale_locations(
        self,
        desired_rows: list[WarehouseLocation],
        existing_rows: dict[str, WarehouseLocation],
    ) -> int:
        """Soft-deactivate locations the new document no longer contains."""
        keep = {row.full_path for row in desired_rows}
        deactivated = 0
        for path, row in existing_rows.items():
            if path in keep or not row.is_active:
                continue
            row.is_active = False
            deactivated += 1
        return deactivated

    def _deactivate_other_plans(
        self, warehouse_id: uuid.UUID, organization_id: uuid.UUID
    ) -> None:
        self.db.query(WarehouseFloorPlan).filter(
            WarehouseFloorPlan.warehouse_id == warehouse_id,
            WarehouseFloorPlan.organization_id == organization_id,
            WarehouseFloorPlan.is_active.is_(True),
        ).update({"is_active": False}, synchronize_session="fetch")

    def _reserve_qr_codes(self, count: int) -> list[str]:
        """Generate QR codes that are unique against the table.

        ``warehouse_locations.qr_code`` carries a table-wide unique constraint, so
        candidates are checked against the database in batches and only the
        collisions are regenerated.
        """
        if count <= 0:
            return []

        codes = generate_qr_codes(count)
        for _ in range(QR_RETRY_ROUNDS):
            taken: set[str] = set()
            for start in range(0, len(codes), QR_CHECK_BATCH):
                batch = codes[start : start + QR_CHECK_BATCH]
                taken.update(
                    code
                    for (code,) in self.db.query(WarehouseLocation.qr_code)
                    .filter(WarehouseLocation.qr_code.in_(batch))
                    .all()
                    if code
                )
            if not taken:
                break
            replacements = generate_qr_codes(len(taken), existing=set(codes))
            for index, code in enumerate(codes):
                if code in taken:
                    codes[index] = replacements.pop()

        return codes

    # ------------------------------------------------------------- lookups

    def _get_warehouse(
        self, warehouse_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Warehouse:
        warehouse = (
            self.db.query(Warehouse)
            .filter(
                Warehouse.id == warehouse_id,
                Warehouse.organization_id == organization_id,
            )
            .first()
        )
        if warehouse is None:
            raise NotFoundError(f"Warehouse {warehouse_id} was not found")
        return warehouse

    def _get_plan(
        self, floor_plan_id: uuid.UUID, organization_id: uuid.UUID
    ) -> WarehouseFloorPlan:
        plan = (
            self.db.query(WarehouseFloorPlan)
            .filter(
                WarehouseFloorPlan.id == floor_plan_id,
                WarehouseFloorPlan.organization_id == organization_id,
            )
            .first()
        )
        if plan is None:
            raise NotFoundError(f"Floor plan {floor_plan_id} was not found")
        return plan

    # --------------------------------------------------------------- mapping

    @staticmethod
    def _blocking_code(compiled: CompiledLayout) -> str | None:
        for diagnostic in compiled.diagnostics:
            if diagnostic.severity == "error":
                return diagnostic.code
        return None

    def _validate_payload(self, compiled: CompiledLayout) -> LayoutValidateResponse:
        return LayoutValidateResponse(
            valid=compiled.errorCount == 0,
            applyable=compiled.applyable,
            summary=self._summary_out(compiled),
            diagnostics=self._diagnostics_out(compiled),
            sample_bin_paths=compiled.sampleBinPaths(8),
        )

    @staticmethod
    def _summary_out(compiled: CompiledLayout) -> LayoutSummaryOut:
        summary = compiled.summary()
        return LayoutSummaryOut(
            zones=summary["zones"],
            aisles=summary["aisles"],
            lanes=summary["lanes"],
            rack_types=summary["rackTypes"],
            obstacles=summary["obstacles"],
            bays=summary["bays"],
            active_bays=summary["activeBays"],
            levels=summary["levels"],
            bins=summary["bins"],
            errors=summary["errors"],
            warnings=summary["warnings"],
        )

    @classmethod
    def _diagnostics_out(cls, compiled: CompiledLayout) -> list[LayoutDiagnosticOut]:
        return [cls._diagnostic_out(item) for item in compiled.diagnostics]

    @staticmethod
    def _diagnostic_out(item: Diagnostic) -> LayoutDiagnosticOut:
        return LayoutDiagnosticOut(
            code=item.code,
            severity=item.severity,
            message=item.message,
            entity_refs=[
                LayoutEntityRefOut(kind=ref.kind, id=ref.id, label=ref.label)
                for ref in item.entityRefs
            ],
            data=item.data,
        )

    @staticmethod
    def _zone_out(zone) -> LayoutZoneOut:
        return LayoutZoneOut(
            code=zone.code,
            ordinal=zone.ordinal,
            path=zone.path,
            aisle_count=zone.aisleCount,
        )

    @staticmethod
    def _bin_out(bin_) -> LayoutBinOut:
        return LayoutBinOut(
            path=bin_.path,
            code=bin_.code,
            label=bin_.label,
            aisle_code=bin_.aisleCode,
            lane_code=bin_.laneCode,
            side=bin_.side,
            bay_seq=bin_.baySeq,
            level_index=bin_.levelIndex,
            level_path=bin_.levelPath,
            x=bin_.centerX,
            y=bin_.centerZ,
            z=bin_.centerY,
            capacity_m3=bin_.capacityM3,
            usable_volume_m3=bin_.usableVolumeM3,
            max_volume_cc=bin_.maxVolumeCc,
            max_weight_kg=bin_.maxWeightKg,
        )

    @staticmethod
    def _plan_out(compiled: CompiledLayout) -> LayoutPlanOut:
        doc = compiled.doc
        if doc is None:
            return LayoutPlanOut(footprint_length_m=0.0, footprint_width_m=0.0)

        return LayoutPlanOut(
            footprint_length_m=doc.warehouse.lengthM,
            footprint_width_m=doc.warehouse.widthM,
            aisles=[
                LayoutAislePlanOut(
                    code=aisle.code,
                    x1=aisle.centerline.x1,
                    z1=aisle.centerline.z1,
                    x2=aisle.centerline.x2,
                    z2=aisle.centerline.z2,
                    width_m=aisle.widthM,
                )
                for aisle in doc.aisles
            ],
            obstacles=[
                LayoutObstacleOut(
                    id=obstacle.label,
                    kind=obstacle.kind,
                    x=obstacle.x,
                    z=obstacle.z,
                    width_m=obstacle.widthM,
                    depth_m=obstacle.depthM,
                    height_m=obstacle.heightM,
                )
                for obstacle in doc.obstacles
            ],
        )
