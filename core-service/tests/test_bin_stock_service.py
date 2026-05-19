"""Unit tests for BinStockService."""

import uuid
from decimal import Decimal

import pytest

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.bin_stock_level import BinStockLevel
from app.models.stock_level import StockLevel
from app.models.warehouse_location import WarehouseLocation
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


class TestAddStock:
    """Tests for add_stock method."""

    def test_add_stock_creates_bin_stock_record(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Adding stock to an empty bin should create a new BinStockLevel record."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=100, total_capacity=100, available_capacity=100,
        )
        db_session.commit()

        result = bin_stock_service.add_stock(
            bin_id=bin_loc.id,
            item_id=item_id,
            quantity=Decimal("25"),
            org_id=org_id,
        )

        assert result.quantity_on_hand == Decimal("25")
        assert result.bin_location_id == bin_loc.id
        assert result.item_id == item_id
        assert result.organization_id == org_id

    def test_add_stock_increments_existing_record(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Adding stock to a bin with existing stock should increment quantity."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=100, total_capacity=100, available_capacity=100,
        )
        db_session.commit()

        bin_stock_service.add_stock(
            bin_id=bin_loc.id, item_id=item_id,
            quantity=Decimal("20"), org_id=org_id,
        )
        result = bin_stock_service.add_stock(
            bin_id=bin_loc.id, item_id=item_id,
            quantity=Decimal("15"), org_id=org_id,
        )

        assert result.quantity_on_hand == Decimal("35")

    def test_add_stock_rejects_exceeding_capacity(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Should reject stock addition that would exceed bin capacity."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=50, total_capacity=50, available_capacity=50,
        )
        db_session.commit()

        with pytest.raises(ValidationError, match="Cannot add"):
            bin_stock_service.add_stock(
                bin_id=bin_loc.id, item_id=item_id,
                quantity=Decimal("60"), org_id=org_id,
            )

    def test_add_stock_rejects_deactivated_bin(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Should reject stock operations on deactivated locations."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=100, total_capacity=100, is_active=False,
        )
        db_session.commit()

        with pytest.raises(StateError, match="deactivated"):
            bin_stock_service.add_stock(
                bin_id=bin_loc.id, item_id=item_id,
                quantity=Decimal("10"), org_id=org_id,
            )

    def test_add_stock_rejects_non_bin_location(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Should reject stock operations on non-bin locations."""
        level_loc = _create_location(
            db_session, org_id, warehouse_id, "level", "L01",
            capacity=100, total_capacity=100,
        )
        db_session.commit()

        with pytest.raises(ValidationError, match="not 'bin'"):
            bin_stock_service.add_stock(
                bin_id=level_loc.id, item_id=item_id,
                quantity=Decimal("10"), org_id=org_id,
            )

    def test_add_stock_rejects_zero_quantity(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Should reject zero or negative quantity."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=100, total_capacity=100,
        )
        db_session.commit()

        with pytest.raises(ValidationError, match="positive"):
            bin_stock_service.add_stock(
                bin_id=bin_loc.id, item_id=item_id,
                quantity=Decimal("0"), org_id=org_id,
            )

    def test_add_stock_syncs_warehouse_stock_levels(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Adding bin stock should sync to warehouse-level stock_levels."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=100, total_capacity=100, available_capacity=100,
        )
        db_session.commit()

        bin_stock_service.add_stock(
            bin_id=bin_loc.id, item_id=item_id,
            quantity=Decimal("30"), org_id=org_id,
        )

        stock_level = (
            db_session.query(StockLevel)
            .filter(
                StockLevel.product_id == item_id,
                StockLevel.warehouse_id == warehouse_id,
            )
            .first()
        )

        assert stock_level is not None
        assert stock_level.quantity_on_hand == 30
        assert stock_level.quantity_available == 30

    def test_add_stock_with_batch_number(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Should support batch-specific stock tracking."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=200, total_capacity=200, available_capacity=200,
        )
        db_session.commit()

        result1 = bin_stock_service.add_stock(
            bin_id=bin_loc.id, item_id=item_id,
            quantity=Decimal("20"), org_id=org_id,
            batch_number="BATCH-A",
        )
        result2 = bin_stock_service.add_stock(
            bin_id=bin_loc.id, item_id=item_id,
            quantity=Decimal("30"), org_id=org_id,
            batch_number="BATCH-B",
        )

        assert result1.quantity_on_hand == Decimal("20")
        assert result1.batch_number == "BATCH-A"
        assert result2.quantity_on_hand == Decimal("30")
        assert result2.batch_number == "BATCH-B"

    def test_add_stock_raises_not_found_for_invalid_bin(
        self, db_session, bin_stock_service, org_id, item_id
    ):
        """Should raise NotFoundError for non-existent bin."""
        with pytest.raises(NotFoundError):
            bin_stock_service.add_stock(
                bin_id=uuid.uuid4(), item_id=item_id,
                quantity=Decimal("10"), org_id=org_id,
            )


class TestRemoveStock:
    """Tests for remove_stock method."""

    def test_remove_stock_decrements_quantity(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Removing stock should decrement the quantity_on_hand."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=100, total_capacity=100, available_capacity=100,
        )
        db_session.commit()

        bin_stock_service.add_stock(
            bin_id=bin_loc.id, item_id=item_id,
            quantity=Decimal("50"), org_id=org_id,
        )
        result = bin_stock_service.remove_stock(
            bin_id=bin_loc.id, item_id=item_id,
            quantity=Decimal("20"), org_id=org_id,
        )

        assert result.quantity_on_hand == Decimal("30")

    def test_remove_stock_rejects_insufficient_quantity(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Should reject removal when insufficient stock on hand."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=100, total_capacity=100, available_capacity=100,
        )
        db_session.commit()

        bin_stock_service.add_stock(
            bin_id=bin_loc.id, item_id=item_id,
            quantity=Decimal("10"), org_id=org_id,
        )

        with pytest.raises(ValidationError, match="Cannot remove"):
            bin_stock_service.remove_stock(
                bin_id=bin_loc.id, item_id=item_id,
                quantity=Decimal("20"), org_id=org_id,
            )

    def test_remove_stock_rejects_deactivated_bin(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Should reject stock removal on deactivated locations."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=100, total_capacity=100, is_active=False,
        )
        db_session.commit()

        with pytest.raises(StateError, match="deactivated"):
            bin_stock_service.remove_stock(
                bin_id=bin_loc.id, item_id=item_id,
                quantity=Decimal("10"), org_id=org_id,
            )

    def test_remove_stock_syncs_warehouse_stock_levels(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Removing bin stock should sync to warehouse-level stock_levels."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=100, total_capacity=100, available_capacity=100,
        )
        db_session.commit()

        bin_stock_service.add_stock(
            bin_id=bin_loc.id, item_id=item_id,
            quantity=Decimal("50"), org_id=org_id,
        )
        bin_stock_service.remove_stock(
            bin_id=bin_loc.id, item_id=item_id,
            quantity=Decimal("20"), org_id=org_id,
        )

        stock_level = (
            db_session.query(StockLevel)
            .filter(
                StockLevel.product_id == item_id,
                StockLevel.warehouse_id == warehouse_id,
            )
            .first()
        )

        assert stock_level is not None
        assert stock_level.quantity_on_hand == 30
        assert stock_level.quantity_available == 30

    def test_remove_stock_raises_not_found_for_no_stock_record(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Should raise NotFoundError when no stock record exists for the item."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=100, total_capacity=100, available_capacity=100,
        )
        db_session.commit()

        with pytest.raises(NotFoundError, match="No stock record"):
            bin_stock_service.remove_stock(
                bin_id=bin_loc.id, item_id=item_id,
                quantity=Decimal("10"), org_id=org_id,
            )

    def test_remove_stock_rejects_zero_quantity(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Should reject zero or negative quantity."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=100, total_capacity=100,
        )
        db_session.commit()

        with pytest.raises(ValidationError, match="positive"):
            bin_stock_service.remove_stock(
                bin_id=bin_loc.id, item_id=item_id,
                quantity=Decimal("-5"), org_id=org_id,
            )


class TestGetBinsForItem:
    """Tests for get_bins_for_item method."""

    def test_returns_bins_with_stock(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Should return all bins containing the specified item."""
        bin1 = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=100, total_capacity=100, available_capacity=100,
        )
        bin2 = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN02",
            capacity=100, total_capacity=100, available_capacity=100,
        )
        db_session.commit()

        bin_stock_service.add_stock(
            bin_id=bin1.id, item_id=item_id,
            quantity=Decimal("20"), org_id=org_id,
        )
        bin_stock_service.add_stock(
            bin_id=bin2.id, item_id=item_id,
            quantity=Decimal("30"), org_id=org_id,
        )

        results = bin_stock_service.get_bins_for_item(item_id, org_id)

        assert len(results) == 2
        quantities = {r["quantity_on_hand"] for r in results}
        assert Decimal("20") in quantities
        assert Decimal("30") in quantities

    def test_returns_empty_list_when_no_stock(
        self, db_session, bin_stock_service, org_id, item_id
    ):
        """Should return empty list when item has no stock anywhere."""
        results = bin_stock_service.get_bins_for_item(item_id, org_id)
        assert results == []

    def test_includes_available_capacity(
        self, db_session, bin_stock_service, org_id, warehouse_id, item_id
    ):
        """Should include available capacity info for each bin."""
        bin1 = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=100, total_capacity=100, available_capacity=100,
        )
        db_session.commit()

        bin_stock_service.add_stock(
            bin_id=bin1.id, item_id=item_id,
            quantity=Decimal("40"), org_id=org_id,
        )

        results = bin_stock_service.get_bins_for_item(item_id, org_id)

        assert len(results) == 1
        assert results[0]["bin_capacity"] == Decimal("100")
        assert results[0]["available_capacity"] == Decimal("60")


class TestGetBinStock:
    """Tests for get_bin_stock method."""

    def test_returns_all_stock_records_for_bin(
        self, db_session, bin_stock_service, org_id, warehouse_id
    ):
        """Should return all stock records for a specific bin."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=200, total_capacity=200, available_capacity=200,
        )
        item1 = uuid.uuid4()
        item2 = uuid.uuid4()
        db_session.commit()

        bin_stock_service.add_stock(
            bin_id=bin_loc.id, item_id=item1,
            quantity=Decimal("20"), org_id=org_id,
        )
        bin_stock_service.add_stock(
            bin_id=bin_loc.id, item_id=item2,
            quantity=Decimal("30"), org_id=org_id,
        )

        results = bin_stock_service.get_bin_stock(bin_loc.id, org_id)

        assert len(results) == 2
        item_ids = {r.item_id for r in results}
        assert item1 in item_ids
        assert item2 in item_ids

    def test_returns_empty_list_for_empty_bin(
        self, db_session, bin_stock_service, org_id, warehouse_id
    ):
        """Should return empty list for a bin with no stock."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id, "bin", "BIN01",
            capacity=100, total_capacity=100,
        )
        db_session.commit()

        results = bin_stock_service.get_bin_stock(bin_loc.id, org_id)
        assert results == []

    def test_raises_not_found_for_invalid_bin(
        self, db_session, bin_stock_service, org_id
    ):
        """Should raise NotFoundError for non-existent bin."""
        with pytest.raises(NotFoundError):
            bin_stock_service.get_bin_stock(uuid.uuid4(), org_id)
