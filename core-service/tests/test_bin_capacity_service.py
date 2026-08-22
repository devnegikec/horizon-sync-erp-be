"""Unit tests for BinCapacityService."""

import uuid
from decimal import Decimal

import pytest

from app.models.bin_stock_level import BinStockLevel
from app.models.item_packaging_unit import ItemPackagingUnit
from app.models.warehouse import Warehouse
from app.models.warehouse_location import WarehouseLocation
from app.services.bin_capacity_service import (
    STATE_ALMOST_FULL,
    STATE_AVAILABLE,
    STATE_EMPTY,
    STATE_FULL,
    BinCapacityService,
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


@pytest.fixture
def service(db_session):
    return BinCapacityService(db_session)


def _create_warehouse(
    db_session,
    org_id,
    warehouse_id,
    use_volume=True,
    use_weight=False,
    full="0.90",
    almost="0.70",
):
    wh = Warehouse(
        id=warehouse_id,
        organization_id=org_id,
        name="Test Warehouse",
        code="WH-01",
        use_volume=use_volume,
        use_weight=use_weight,
        full_threshold_pct=Decimal(full),
        almost_full_threshold_pct=Decimal(almost),
    )
    db_session.add(wh)
    db_session.flush()
    return wh


def _create_location(
    db_session,
    org_id,
    warehouse_id,
    location_type,
    code,
    parent_id=None,
    max_volume_cc=None,
    max_weight_grams=None,
    full_threshold_pct=None,
    almost_full_threshold_pct=None,
):
    loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=org_id,
        warehouse_id=warehouse_id,
        parent_location_id=parent_id,
        location_type=location_type,
        code=code,
        full_path=code,
        max_volume_cc=Decimal(str(max_volume_cc))
        if max_volume_cc is not None
        else None,
        max_weight_grams=Decimal(str(max_weight_grams))
        if max_weight_grams is not None
        else None,
        full_threshold_pct=Decimal(str(full_threshold_pct))
        if full_threshold_pct is not None
        else None,
        almost_full_threshold_pct=Decimal(str(almost_full_threshold_pct))
        if almost_full_threshold_pct is not None
        else None,
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


class TestGetBinCapacity:
    def test_empty_bin(self, db_session, service, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN-01", max_volume_cc=100000
        )

        result = service.get_bin_capacity(bin_loc.id, org_id)

        assert result["binding_pct"] == Decimal("0")
        assert result["bin_state"] == STATE_EMPTY
        assert result["is_available"] is True
        assert result["volume"]["pct"] == Decimal("0")

    def test_volume_percentage(
        self, db_session, service, org_id, warehouse_id, item_id
    ):
        _create_warehouse(db_session, org_id, warehouse_id)
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN-01", max_volume_cc=100000
        )
        pu = _create_packaging_unit(db_session, org_id, item_id)
        _add_stock(
            db_session,
            org_id,
            bin_loc.id,
            item_id,
            Decimal("50"),
            packaging_unit_id=pu.id,
        )

        result = service.get_bin_capacity(bin_loc.id, org_id)

        # 50 units × 0.001 m³ = 0.05 m³ in a 0.1 m³ bin → 50%
        assert result["volume"]["pct"] == Decimal("50")
        assert result["binding_pct"] == Decimal("50")
        assert result["bin_state"] == STATE_AVAILABLE


class TestStateDerivation:
    def test_four_state_bands(self, db_session, service, org_id, warehouse_id, item_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        pu = _create_packaging_unit(db_session, org_id, item_id)

        expected = [
            (Decimal("0"), STATE_EMPTY),
            (Decimal("50"), STATE_AVAILABLE),
            (Decimal("75"), STATE_ALMOST_FULL),
            (Decimal("95"), STATE_FULL),
        ]
        for i, (qty, state) in enumerate(expected):
            bin_loc = _create_location(
                db_session,
                org_id,
                warehouse_id,
                "bin",
                f"BIN-{i}",
                max_volume_cc=100000,
            )
            if qty > 0:
                _add_stock(
                    db_session,
                    org_id,
                    bin_loc.id,
                    item_id,
                    qty,
                    packaging_unit_id=pu.id,
                )
            result = service.get_bin_capacity(bin_loc.id, org_id)
            assert result["bin_state"] == state, f"qty {qty} → {result['bin_state']}"


class TestConfigurableDimensions:
    def test_weight_excluded_by_default(
        self, db_session, service, org_id, warehouse_id, item_id
    ):
        _create_warehouse(
            db_session, org_id, warehouse_id, use_volume=True, use_weight=False
        )
        bin_loc = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN-01",
            max_volume_cc=100000,
            max_weight_grams=1000,
        )
        pu = _create_packaging_unit(db_session, org_id, item_id, weight=200)
        _add_stock(
            db_session,
            org_id,
            bin_loc.id,
            item_id,
            Decimal("2"),
            packaging_unit_id=pu.id,
        )

        result = service.get_bin_capacity(bin_loc.id, org_id)

        assert result["weight"]["pct"] is None
        assert result["weight"]["capacity_kg"] is None
        assert result["binding_pct"] == result["volume"]["pct"]

    def test_weight_included_when_enabled(
        self, db_session, service, org_id, warehouse_id, item_id
    ):
        _create_warehouse(
            db_session, org_id, warehouse_id, use_volume=True, use_weight=True
        )
        bin_loc = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN-01",
            max_weight_grams=1000,
        )
        pu = _create_packaging_unit(db_session, org_id, item_id, weight=200)
        _add_stock(
            db_session,
            org_id,
            bin_loc.id,
            item_id,
            Decimal("2"),
            packaging_unit_id=pu.id,
        )

        result = service.get_bin_capacity(bin_loc.id, org_id)

        # 2 × 200g = 400g = 0.4kg in a 1kg bin → 40%
        assert result["weight"]["pct"] == Decimal("40")
        assert result["binding_pct"] == Decimal("40")


class TestThresholds:
    def test_bin_threshold_override(
        self, db_session, service, org_id, warehouse_id, item_id
    ):
        _create_warehouse(db_session, org_id, warehouse_id, full="0.90")
        bin_loc = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN-01",
            max_volume_cc=100000,
            full_threshold_pct="0.50",
        )
        pu = _create_packaging_unit(db_session, org_id, item_id)
        # 60% → above the bin's 50% override → full
        _add_stock(
            db_session,
            org_id,
            bin_loc.id,
            item_id,
            Decimal("60"),
            packaging_unit_id=pu.id,
        )

        result = service.get_bin_capacity(bin_loc.id, org_id)
        assert result["bin_state"] == STATE_FULL


class TestRefreshBin:
    def test_refresh_persists_cached_state(
        self, db_session, service, org_id, warehouse_id, item_id
    ):
        _create_warehouse(db_session, org_id, warehouse_id)
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN-01", max_volume_cc=100000
        )
        pu = _create_packaging_unit(db_session, org_id, item_id)
        _add_stock(
            db_session,
            org_id,
            bin_loc.id,
            item_id,
            Decimal("75"),
            packaging_unit_id=pu.id,
        )
        db_session.commit()

        service.refresh_bin(bin_loc.id, org_id)
        db_session.commit()
        db_session.refresh(bin_loc)

        assert bin_loc.bin_state == STATE_ALMOST_FULL
        assert bin_loc.is_available is True
        assert bin_loc.capacity_volume_pct == Decimal("75")

    def test_refresh_warehouse_counts_bins(
        self, db_session, service, org_id, warehouse_id
    ):
        _create_warehouse(db_session, org_id, warehouse_id)
        _create_location(db_session, org_id, warehouse_id, "bin", "BIN-01")
        _create_location(db_session, org_id, warehouse_id, "bin", "BIN-02")
        db_session.commit()

        count = service.refresh_warehouse(warehouse_id, org_id)
        assert count == 2


class TestGetAvailableBins:
    def test_put_away_excludes_full_bins(
        self, db_session, service, org_id, warehouse_id, item_id
    ):
        _create_warehouse(db_session, org_id, warehouse_id)
        full_bin = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN-FULL", max_volume_cc=100000
        )
        empty_bin = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN-EMPTY", max_volume_cc=100000
        )
        pu = _create_packaging_unit(db_session, org_id, item_id)
        _add_stock(
            db_session,
            org_id,
            full_bin.id,
            item_id,
            Decimal("95"),
            packaging_unit_id=pu.id,
        )

        results = service.get_available_bins(warehouse_id, org_id, task_type="put_away")
        ids = {r["bin_id"] for r in results}

        assert empty_bin.id in ids
        assert full_bin.id not in ids

    def test_pick_requires_stock(
        self, db_session, service, org_id, warehouse_id, item_id
    ):
        _create_warehouse(db_session, org_id, warehouse_id)
        stocked = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN-STOCK", max_volume_cc=100000
        )
        empty = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN-EMPTY", max_volume_cc=100000
        )
        pu = _create_packaging_unit(db_session, org_id, item_id)
        _add_stock(
            db_session,
            org_id,
            stocked.id,
            item_id,
            Decimal("10"),
            packaging_unit_id=pu.id,
        )

        results = service.get_available_bins(warehouse_id, org_id, task_type="pick")
        ids = {r["bin_id"] for r in results}

        assert stocked.id in ids
        assert empty.id not in ids


class TestGetCapacityTree:
    def test_rollup_bin_to_aisle_to_warehouse(
        self, db_session, service, org_id, warehouse_id, item_id
    ):
        _create_warehouse(db_session, org_id, warehouse_id)
        aisle = _create_location(db_session, org_id, warehouse_id, "aisle", "AISLE-01")
        bin_loc = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN-01",
            parent_id=aisle.id,
            max_volume_cc=100000,
        )
        pu = _create_packaging_unit(db_session, org_id, item_id)
        _add_stock(
            db_session,
            org_id,
            bin_loc.id,
            item_id,
            Decimal("50"),
            packaging_unit_id=pu.id,
        )

        tree = service.get_capacity_tree(warehouse_id, org_id)

        assert tree["level"] == "warehouse"
        assert tree["volume"]["occupied_m3"] == Decimal("0.05")
        assert tree["children"][0]["level"] == "aisle"
        assert tree["children"][0]["volume"]["occupied_m3"] == Decimal("0.05")
        bin_node = tree["children"][0]["children"][0]
        assert bin_node["level"] == "bin"
        assert bin_node["bin_state"] == STATE_AVAILABLE


class TestGetBinStates:
    def test_returns_positions_and_states(
        self, db_session, service, org_id, warehouse_id, item_id
    ):
        _create_warehouse(db_session, org_id, warehouse_id)
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN-01", max_volume_cc=100000
        )

        states = service.get_bin_states(warehouse_id, org_id)

        assert len(states) == 1
        assert states[0]["bin_id"] == bin_loc.id
        assert states[0]["bin_state"] == STATE_EMPTY
