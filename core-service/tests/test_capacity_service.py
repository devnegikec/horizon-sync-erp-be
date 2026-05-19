"""Unit tests for CapacityService."""

import uuid
from decimal import Decimal

import pytest

from app.models.bin_stock_level import BinStockLevel
from app.models.warehouse_location import WarehouseLocation
from app.services.capacity_service import CapacityService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    return uuid.uuid4()


@pytest.fixture
def capacity_service(db_session):
    return CapacityService(db_session)


def _create_location(
    db_session,
    org_id,
    warehouse_id,
    location_type,
    code,
    parent_id=None,
    capacity=0,
    total_capacity=0,
    available_capacity=0,
    is_active=True,
):
    """Helper to create a warehouse location."""
    loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=org_id,
        warehouse_id=warehouse_id,
        parent_location_id=parent_id,
        location_type=location_type,
        code=code,
        full_path=code,
        capacity=Decimal(str(capacity)),
        total_capacity=Decimal(str(total_capacity)),
        available_capacity=Decimal(str(available_capacity)),
        is_active=is_active,
        version=1,
    )
    db_session.add(loc)
    db_session.flush()
    return loc


def _add_stock(db_session, org_id, bin_id, item_id, quantity):
    """Helper to add stock to a bin."""
    stock = BinStockLevel(
        id=uuid.uuid4(),
        organization_id=org_id,
        bin_location_id=bin_id,
        item_id=item_id,
        quantity_on_hand=Decimal(str(quantity)),
        batch_number="BATCH-001",
    )
    db_session.add(stock)
    db_session.flush()
    return stock


class TestRecalculateAncestors:
    """Tests for recalculate_ancestors method."""

    def test_recalculates_parent_total_capacity_from_children(
        self, db_session, capacity_service, org_id, warehouse_id
    ):
        """Parent total_capacity should equal sum of children's total_capacity."""
        zone = _create_location(db_session, org_id, warehouse_id, "zone", "Z01")
        aisle = _create_location(
            db_session, org_id, warehouse_id, "aisle", "A01", parent_id=zone.id
        )
        bay = _create_location(
            db_session, org_id, warehouse_id, "bay", "B01", parent_id=aisle.id
        )
        level = _create_location(
            db_session, org_id, warehouse_id, "level", "L01", parent_id=bay.id
        )
        bin1 = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            parent_id=level.id,
            capacity=100,
            total_capacity=100,
        )
        _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN02",
            parent_id=level.id,
            capacity=50,
            total_capacity=50,
        )
        db_session.commit()

        # Trigger recalculation from bin1
        capacity_service.recalculate_ancestors(bin1.id)
        db_session.commit()

        # Refresh to get updated values
        db_session.refresh(level)
        db_session.refresh(bay)
        db_session.refresh(aisle)
        db_session.refresh(zone)

        # Level should have total_capacity = 100 + 50 = 150
        assert level.total_capacity == Decimal("150")
        assert bay.total_capacity == Decimal("150")
        assert aisle.total_capacity == Decimal("150")
        assert zone.total_capacity == Decimal("150")

    def test_recalculates_available_capacity_with_stock(
        self, db_session, capacity_service, org_id, warehouse_id
    ):
        """Available capacity should be total_capacity minus stock in subtree."""
        zone = _create_location(db_session, org_id, warehouse_id, "zone", "Z01")
        level = _create_location(
            db_session, org_id, warehouse_id, "level", "L01", parent_id=zone.id
        )
        bin1 = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            parent_id=level.id,
            capacity=100,
            total_capacity=100,
        )
        db_session.flush()

        # Add stock to the bin
        item_id = uuid.uuid4()
        _add_stock(db_session, org_id, bin1.id, item_id, 30)
        db_session.commit()

        # Trigger recalculation
        capacity_service.recalculate_ancestors(bin1.id)
        db_session.commit()

        db_session.refresh(level)
        db_session.refresh(zone)

        # Level total = 100, used = 30, available = 70
        assert level.total_capacity == Decimal("100")
        assert level.available_capacity == Decimal("70")
        assert zone.total_capacity == Decimal("100")
        assert zone.available_capacity == Decimal("70")

    def test_deactivated_children_excluded_from_rollup(
        self, db_session, capacity_service, org_id, warehouse_id
    ):
        """Deactivated locations should not contribute to parent capacity."""
        level = _create_location(db_session, org_id, warehouse_id, "level", "L01")
        bin1 = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            parent_id=level.id,
            capacity=100,
            total_capacity=100,
        )
        _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN02",
            parent_id=level.id,
            capacity=50,
            total_capacity=50,
            is_active=False,
        )
        db_session.commit()

        capacity_service.recalculate_ancestors(bin1.id)
        db_session.commit()

        db_session.refresh(level)
        # Only active bin1 should count
        assert level.total_capacity == Decimal("100")

    def test_raises_not_found_for_invalid_location(self, db_session, capacity_service):
        """Should raise NotFoundError for non-existent location."""
        from app.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            capacity_service.recalculate_ancestors(uuid.uuid4())

    def test_increments_version_on_update(
        self, db_session, capacity_service, org_id, warehouse_id
    ):
        """Version should increment after capacity update."""
        level = _create_location(db_session, org_id, warehouse_id, "level", "L01")
        bin1 = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            parent_id=level.id,
            capacity=100,
            total_capacity=100,
        )
        db_session.commit()

        initial_version = level.version
        capacity_service.recalculate_ancestors(bin1.id)
        db_session.commit()

        db_session.refresh(level)
        assert level.version == initial_version + 1


class TestComputeAvailableCapacity:
    """Tests for compute_available_capacity method."""

    def test_returns_total_minus_stock(
        self, db_session, capacity_service, org_id, warehouse_id
    ):
        """Available = total_capacity - stock in subtree."""
        bin1 = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            capacity=200,
            total_capacity=200,
        )
        item_id = uuid.uuid4()
        _add_stock(db_session, org_id, bin1.id, item_id, 75)
        db_session.commit()

        available = capacity_service.compute_available_capacity(bin1.id, org_id)
        assert available == Decimal("125")

    def test_returns_full_capacity_when_no_stock(
        self, db_session, capacity_service, org_id, warehouse_id
    ):
        """Available should equal total when no stock exists."""
        bin1 = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            capacity=200,
            total_capacity=200,
        )
        db_session.commit()

        available = capacity_service.compute_available_capacity(bin1.id, org_id)
        assert available == Decimal("200")

    def test_raises_not_found_for_wrong_org(
        self, db_session, capacity_service, org_id, warehouse_id
    ):
        """Should raise NotFoundError when org doesn't match."""
        from app.core.exceptions import NotFoundError

        bin1 = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            capacity=200,
            total_capacity=200,
        )
        db_session.commit()

        other_org = uuid.uuid4()
        with pytest.raises(NotFoundError):
            capacity_service.compute_available_capacity(bin1.id, other_org)


class TestGetCapacitySummary:
    """Tests for get_capacity_summary method."""

    def test_returns_correct_summary(
        self, db_session, capacity_service, org_id, warehouse_id
    ):
        """Should return a complete capacity summary."""
        level = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "level",
            "L01",
            total_capacity=200,
            available_capacity=200,
        )
        bin1 = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            parent_id=level.id,
            capacity=100,
            total_capacity=100,
        )
        _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN02",
            parent_id=level.id,
            capacity=100,
            total_capacity=100,
        )
        item_id = uuid.uuid4()
        _add_stock(db_session, org_id, bin1.id, item_id, 40)
        db_session.commit()

        summary = capacity_service.get_capacity_summary(level.id, org_id)

        assert summary["location_id"] == level.id
        assert summary["location_type"] == "level"
        assert summary["total_capacity"] == Decimal("200")
        assert summary["used_capacity"] == Decimal("40")
        assert summary["available_capacity"] == Decimal("160")
        assert summary["total_bins"] == 2
        assert summary["occupied_bins"] == 1
        assert summary["active_children"] == 2

    def test_utilization_percentage(
        self, db_session, capacity_service, org_id, warehouse_id
    ):
        """Should calculate correct utilization percentage."""
        bin1 = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            capacity=100,
            total_capacity=100,
        )
        item_id = uuid.uuid4()
        _add_stock(db_session, org_id, bin1.id, item_id, 50)
        db_session.commit()

        summary = capacity_service.get_capacity_summary(bin1.id, org_id)
        assert summary["utilization_percentage"] == Decimal("50.00")

    def test_zero_capacity_no_division_error(
        self, db_session, capacity_service, org_id, warehouse_id
    ):
        """Should handle zero capacity without division error."""
        bin1 = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            capacity=0,
            total_capacity=0,
        )
        db_session.commit()

        summary = capacity_service.get_capacity_summary(bin1.id, org_id)
        assert summary["utilization_percentage"] == Decimal("0")


class TestUpdateLocationCapacity:
    """Tests for update_location_capacity method."""

    def test_updates_bin_capacity_and_triggers_rollup(
        self, db_session, capacity_service, org_id, warehouse_id
    ):
        """Updating a bin's capacity should propagate to ancestors."""
        zone = _create_location(db_session, org_id, warehouse_id, "zone", "Z01")
        bin1 = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            parent_id=zone.id,
            capacity=50,
            total_capacity=50,
        )
        db_session.commit()

        capacity_service.update_location_capacity(bin1.id, Decimal("200"))
        db_session.commit()

        db_session.refresh(bin1)
        db_session.refresh(zone)

        assert bin1.capacity == Decimal("200")
        assert bin1.total_capacity == Decimal("200")
        assert zone.total_capacity == Decimal("200")

    def test_updates_available_capacity_considering_stock(
        self, db_session, capacity_service, org_id, warehouse_id
    ):
        """Available capacity should account for existing stock."""
        bin1 = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            capacity=100,
            total_capacity=100,
        )
        item_id = uuid.uuid4()
        _add_stock(db_session, org_id, bin1.id, item_id, 30)
        db_session.commit()

        capacity_service.update_location_capacity(bin1.id, Decimal("150"))
        db_session.commit()

        db_session.refresh(bin1)
        assert bin1.total_capacity == Decimal("150")
        assert bin1.available_capacity == Decimal("120")
