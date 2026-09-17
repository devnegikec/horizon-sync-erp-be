"""Unit tests for shared volume/weight capacity math (capacity_math)."""

import uuid
from decimal import Decimal

import pytest

from app.models.bin_stock_level import BinStockLevel
from app.models.item_packaging_unit import ItemPackagingUnit
from app.models.warehouse_location import WarehouseLocation
from app.services.capacity_math import (
    G_PER_KG,
    MM3_PER_M3,
    compute_bin_occupancy,
    compute_warehouse_bin_occupancy,
)


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    return uuid.uuid4()


@pytest.fixture
def item_id():
    return uuid.uuid4()


def _create_bin(db_session, org_id, warehouse_id, code="BIN-01"):
    loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=org_id,
        warehouse_id=warehouse_id,
        location_type="bin",
        code=code,
        full_path=code,
        is_active=True,
        version=1,
    )
    db_session.add(loc)
    db_session.flush()
    return loc


def _create_packaging_unit(
    db_session, org_id, item_id, length=100, width=100, height=100, weight=200
):
    pu = ItemPackagingUnit(
        id=uuid.uuid4(),
        organization_id=org_id,
        item_id=item_id,
        unit_name="Each",
        conversion_factor=Decimal("1"),
        length_mm=Decimal(str(length)),
        width_mm=Decimal(str(width)),
        height_mm=Decimal(str(height)),
        weight_grams=Decimal(str(weight)),
        is_base_unit=True,
        is_active=True,
    )
    db_session.add(pu)
    db_session.flush()
    return pu


def _add_stock(db_session, org_id, bin_id, item_id, quantity, packaging_unit_id=None):
    stock = BinStockLevel(
        id=uuid.uuid4(),
        organization_id=org_id,
        bin_location_id=bin_id,
        item_id=item_id,
        quantity_on_hand=Decimal(str(quantity)),
        batch_number="BATCH-001",
        packaging_unit_id=packaging_unit_id,
    )
    db_session.add(stock)
    db_session.flush()
    return stock


class TestComputeBinOccupancy:
    def test_empty_bin_returns_zero(self, db_session, org_id, warehouse_id):
        bin_loc = _create_bin(db_session, org_id, warehouse_id)
        m3, kg = compute_bin_occupancy(db_session, bin_loc.id)
        assert m3 == Decimal("0")
        assert kg == Decimal("0")

    def test_occupancy_uses_packaging_dimensions(
        self, db_session, org_id, warehouse_id, item_id
    ):
        bin_loc = _create_bin(db_session, org_id, warehouse_id)
        pu = _create_packaging_unit(db_session, org_id, item_id)
        _add_stock(
            db_session, org_id, bin_loc.id, item_id, Decimal("5"), packaging_unit_id=pu.id
        )

        m3, kg = compute_bin_occupancy(db_session, bin_loc.id)

        assert m3 == (
            Decimal("100") * Decimal("100") * Decimal("100") * Decimal("5") / MM3_PER_M3
        )
        assert kg == Decimal("200") * Decimal("5") / G_PER_KG

    def test_falls_back_to_base_unit_when_packaging_id_missing(
        self, db_session, org_id, warehouse_id, item_id
    ):
        bin_loc = _create_bin(db_session, org_id, warehouse_id)
        _create_packaging_unit(db_session, org_id, item_id)
        # No packaging_unit_id on the stock row → must fall back to base unit.
        _add_stock(db_session, org_id, bin_loc.id, item_id, Decimal("2"), packaging_unit_id=None)

        m3, kg = compute_bin_occupancy(db_session, bin_loc.id)

        assert m3 == Decimal("100") * Decimal("100") * Decimal("100") * Decimal("2") / MM3_PER_M3
        assert kg == Decimal("200") * Decimal("2") / G_PER_KG

    def test_toggles_skip_dimensions(
        self, db_session, org_id, warehouse_id, item_id
    ):
        bin_loc = _create_bin(db_session, org_id, warehouse_id)
        pu = _create_packaging_unit(db_session, org_id, item_id)
        _add_stock(db_session, org_id, bin_loc.id, item_id, Decimal("3"), packaging_unit_id=pu.id)

        m3_vol, kg_zero = compute_bin_occupancy(
            db_session, bin_loc.id, use_volume=True, use_weight=False
        )
        m3_zero, kg_wt = compute_bin_occupancy(
            db_session, bin_loc.id, use_volume=False, use_weight=True
        )

        assert m3_vol > Decimal("0")
        assert kg_zero == Decimal("0")
        assert m3_zero == Decimal("0")
        assert kg_wt > Decimal("0")

    def test_missing_dimensions_contribute_zero(
        self, db_session, org_id, warehouse_id, item_id
    ):
        bin_loc = _create_bin(db_session, org_id, warehouse_id)
        # No packaging unit at all for the item.
        _add_stock(db_session, org_id, bin_loc.id, item_id, Decimal("10"))

        m3, kg = compute_bin_occupancy(db_session, bin_loc.id)
        assert m3 == Decimal("0")
        assert kg == Decimal("0")


class TestComputeWarehouseBinOccupancy:
    def test_returns_per_bin_occupancy(self, db_session, org_id, warehouse_id, item_id):
        bin1 = _create_bin(db_session, org_id, warehouse_id, code="BIN-01")
        bin2 = _create_bin(db_session, org_id, warehouse_id, code="BIN-02")
        pu = _create_packaging_unit(db_session, org_id, item_id)
        _add_stock(db_session, org_id, bin1.id, item_id, Decimal("2"), packaging_unit_id=pu.id)

        occ = compute_warehouse_bin_occupancy(db_session, warehouse_id)

        assert str(bin1.id) in occ
        assert str(bin2.id) in occ
        assert occ[str(bin1.id)][0] > Decimal("0")
        assert occ[str(bin2.id)][0] == Decimal("0")
