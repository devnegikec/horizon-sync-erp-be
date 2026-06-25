"""Unit tests for FloorPlanGeneratorService (Phase 0 — Dynamic Layout Designer)."""

import uuid

import pytest

from app.core.exceptions import NotFoundError
from app.models.warehouse import Warehouse
from app.models.warehouse_location import WarehouseLocation
from app.schemas.floor_plan import AisleSpec, FloorPlanConfig, ZoneSpec
from app.services.floor_plan_generator_service import FloorPlanGeneratorService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    return uuid.uuid4()


@pytest.fixture
def service(db_session):
    return FloorPlanGeneratorService(db_session)


def _create_warehouse(db_session, warehouse_id, org_id, code="WH1"):
    wh = Warehouse(
        id=warehouse_id,
        organization_id=org_id,
        name="Test Warehouse",
        code=code,
        warehouse_type="warehouse",
    )
    db_session.add(wh)
    db_session.flush()
    return wh


def _simple_config() -> FloorPlanConfig:
    """One zone, one aisle, 2 bays × 3 levels × 1 bin = 6 bins."""
    return FloorPlanConfig(
        grid_unit=1.0,
        zones=[
            ZoneSpec(
                code="A",
                name="Zone A",
                grid_x=0.0,
                grid_y=0.0,
                aisles=[
                    AisleSpec(
                        code="A01",
                        orientation="x",
                        grid_x=0.0,
                        grid_y=0.0,
                        num_bays=2,
                        bay_spacing=1.5,
                        num_levels=3,
                        bins_per_level=1,
                        bin_capacity=100.0,
                    )
                ],
            )
        ],
    )


class TestPreview:
    def test_preview_counts_match_config(
        self, db_session, service, org_id, warehouse_id
    ):
        _create_warehouse(db_session, warehouse_id, org_id)
        result = service.preview(warehouse_id, org_id, _simple_config())

        s = result.summary
        assert s.zone_count == 1
        assert s.aisle_count == 1
        assert s.bay_count == 2
        assert s.level_count == 6  # 2 bays × 3 levels
        assert s.bin_count == 6    # 6 levels × 1 bin

    def test_preview_does_not_persist(
        self, db_session, service, org_id, warehouse_id
    ):
        _create_warehouse(db_session, warehouse_id, org_id)
        service.preview(warehouse_id, org_id, _simple_config())

        count = (
            db_session.query(WarehouseLocation)
            .filter(WarehouseLocation.warehouse_id == warehouse_id)
            .count()
        )
        assert count == 0

    def test_preview_unknown_warehouse_raises(self, service, org_id):
        with pytest.raises(NotFoundError):
            service.preview(uuid.uuid4(), org_id, _simple_config())


class TestApply:
    def test_apply_persists_full_hierarchy(
        self, db_session, service, org_id, warehouse_id
    ):
        _create_warehouse(db_session, warehouse_id, org_id)
        result = service.apply(
            warehouse_id, org_id, _simple_config(), name="v1"
        )

        # 1 zone + 1 aisle + 2 bays + 6 levels + 6 bins = 16 locations
        assert result.locations_created == 16
        persisted = (
            db_session.query(WarehouseLocation)
            .filter(WarehouseLocation.warehouse_id == warehouse_id)
            .count()
        )
        assert persisted == 16

    def test_apply_generates_expected_bin_codes(
        self, db_session, service, org_id, warehouse_id
    ):
        _create_warehouse(db_session, warehouse_id, org_id, code="WH1")
        service.apply(warehouse_id, org_id, _simple_config(), name="v1")

        bins = (
            db_session.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.location_type == "bin",
            )
            .all()
        )
        codes = {b.code for b in bins}
        # Bay 1, levels 1..3
        assert "WH1-A-A01-B01-L1" in codes
        assert "WH1-A-A01-B01-L3" in codes
        # Bay 2, level 1
        assert "WH1-A-A01-B02-L1" in codes

    def test_apply_assigns_z_by_level(
        self, db_session, service, org_id, warehouse_id
    ):
        _create_warehouse(db_session, warehouse_id, org_id)
        service.apply(warehouse_id, org_id, _simple_config(), name="v1")

        l1 = (
            db_session.query(WarehouseLocation)
            .filter(WarehouseLocation.code == "WH1-A-A01-B01-L1")
            .first()
        )
        l3 = (
            db_session.query(WarehouseLocation)
            .filter(WarehouseLocation.code == "WH1-A-A01-B01-L3")
            .first()
        )
        assert float(l1.position_z) == 0.0
        assert float(l3.position_z) == 2.0

    def test_apply_x_orientation_spaces_bays_along_x(
        self, db_session, service, org_id, warehouse_id
    ):
        _create_warehouse(db_session, warehouse_id, org_id)
        service.apply(warehouse_id, org_id, _simple_config(), name="v1")

        b1 = (
            db_session.query(WarehouseLocation)
            .filter(WarehouseLocation.code == "WH1-A-A01-B01")
            .first()
        )
        b2 = (
            db_session.query(WarehouseLocation)
            .filter(WarehouseLocation.code == "WH1-A-A01-B02")
            .first()
        )
        # bay_spacing = 1.5, x orientation → B02.x = B01.x + 1.5, same y
        assert float(b2.position_x) - float(b1.position_x) == pytest.approx(1.5)
        assert float(b2.position_y) == float(b1.position_y)

    def test_apply_replace_existing_deactivates_old(
        self, db_session, service, org_id, warehouse_id
    ):
        _create_warehouse(db_session, warehouse_id, org_id)
        # Seed a pre-existing active location
        old = WarehouseLocation(
            id=uuid.uuid4(),
            organization_id=org_id,
            warehouse_id=warehouse_id,
            location_type="bin",
            code="OLD-BIN",
            is_active=True,
        )
        db_session.add(old)
        db_session.commit()

        result = service.apply(
            warehouse_id, org_id, _simple_config(), name="v2", replace_existing=True
        )

        assert result.locations_deleted == 1
        db_session.refresh(old)
        assert old.is_active is False
