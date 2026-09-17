"""Tests that bin-stock changes trigger capacity refresh (mobile-app trigger points)."""

import uuid
from decimal import Decimal

import pytest

from app.models.item_packaging_unit import ItemPackagingUnit
from app.models.warehouse import Warehouse
from app.models.warehouse_location import WarehouseLocation
from app.services.bin_capacity_service import STATE_AVAILABLE, STATE_FULL
from app.services.bin_stock_service import BinStockService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    return uuid.uuid4()


@pytest.fixture
def item_id():
    return uuid.uuid4()


@pytest.fixture
def bin_stock_service(db_session):
    return BinStockService(db_session)


def _create_warehouse(db_session, org_id, warehouse_id):
    wh = Warehouse(
        id=warehouse_id,
        organization_id=org_id,
        name="Test Warehouse",
        code="WH-01",
        use_volume=True,
        use_weight=False,
        full_threshold_pct=Decimal("0.90"),
        almost_full_threshold_pct=Decimal("0.70"),
    )
    db_session.add(wh)
    db_session.flush()
    return wh


def _create_bin(db_session, org_id, warehouse_id, code, max_volume_cc):
    loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=org_id,
        warehouse_id=warehouse_id,
        location_type="bin",
        code=code,
        full_path=code,
        max_volume_cc=Decimal(str(max_volume_cc)),
        capacity=Decimal("0"),
        is_active=True,
        version=1,
    )
    db_session.add(loc)
    db_session.flush()
    return loc


def _create_base_packaging_unit(db_session, org_id, item_id):
    pu = ItemPackagingUnit(
        id=uuid.uuid4(),
        organization_id=org_id,
        item_id=item_id,
        unit_name="Each",
        conversion_factor=Decimal("1"),
        length_mm=Decimal("100"),
        width_mm=Decimal("100"),
        height_mm=Decimal("100"),
        weight_grams=Decimal("200"),
        is_base_unit=True,
        is_active=True,
    )
    db_session.add(pu)
    db_session.flush()
    return pu


class TestAddStockTriggersCapacityRefresh:
    def test_add_stock_sets_state_and_availability(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        _create_warehouse(db_session, org_id, warehouse_id)
        bin_loc = _create_bin(db_session, org_id, warehouse_id, "BIN-01", max_volume_cc=100000)
        _create_base_packaging_unit(db_session, org_id, item_id)
        db_session.commit()

        bin_stock_service.add_stock(
            bin_id=bin_loc.id,
            item_id=item_id,
            quantity=Decimal("95"),
            org_id=org_id,
        )

        db_session.refresh(bin_loc)
        # 95 units × 0.001 m³ = 95% of 0.1 m³ → full
        assert bin_loc.bin_state == STATE_FULL
        assert bin_loc.is_available is False

    def test_remove_stock_resets_state(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        _create_warehouse(db_session, org_id, warehouse_id)
        bin_loc = _create_bin(db_session, org_id, warehouse_id, "BIN-01", max_volume_cc=100000)
        _create_base_packaging_unit(db_session, org_id, item_id)
        db_session.commit()

        bin_stock_service.add_stock(
            bin_id=bin_loc.id,
            item_id=item_id,
            quantity=Decimal("95"),
            org_id=org_id,
        )
        db_session.refresh(bin_loc)
        assert bin_loc.bin_state == STATE_FULL

        bin_stock_service.remove_stock(
            bin_id=bin_loc.id,
            item_id=item_id,
            quantity=Decimal("45"),
            org_id=org_id,
        )

        db_session.refresh(bin_loc)
        # 50 units left → 50% → available
        assert bin_loc.bin_state == STATE_AVAILABLE
        assert bin_loc.is_available is True
