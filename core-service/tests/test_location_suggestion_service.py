"""Unit tests for LocationSuggestionService (smart location engine)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import NotFoundError
from app.models.bin_stock_level import BinStockLevel
from app.models.item import Item
from app.models.location_allocation import LocationAllocation
from app.models.warehouse_location import WarehouseLocation
from app.services.bin_reservation_service import BinReservationService
from app.services.location_suggestion_service import LocationSuggestionService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    return uuid.uuid4()


@pytest.fixture
def suggest_service(db_session):
    return LocationSuggestionService(db_session)


@pytest.fixture
def reservation_service(db_session):
    return BinReservationService(db_session)


def _create_bin(
    db_session,
    org_id,
    warehouse_id,
    code="BIN01",
    capacity=100,
    max_volume_cc=None,
    x=0,
    y=0,
    z=0,
):
    loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=org_id,
        warehouse_id=warehouse_id,
        location_type="bin",
        code=code,
        full_path=code,
        capacity=Decimal(str(capacity)),
        max_volume_cc=Decimal(str(max_volume_cc))
        if max_volume_cc is not None
        else None,
        position_x=Decimal(str(x)),
        position_y=Decimal(str(y)),
        position_z=Decimal(str(z)),
        is_active=True,
        version=1,
    )
    db_session.add(loc)
    db_session.commit()
    return loc


def _create_item(db_session, org_id, item_code="SKU001", name="Test Item"):
    item = Item(
        id=uuid.uuid4(),
        organization_id=org_id,
        item_code=item_code,
        item_name=name,
        item_type="stock",
        uom="Nos",
        maintain_stock=True,
    )
    db_session.add(item)
    db_session.commit()
    return item


def _create_packaging_unit(
    db_session, org_id, item_id, length=100, width=100, height=100
):
    from app.models.item_packaging_unit import ItemPackagingUnit

    pu = ItemPackagingUnit(
        id=uuid.uuid4(),
        organization_id=org_id,
        item_id=item_id,
        unit_name="Each",
        conversion_factor=Decimal("1"),
        length_mm=Decimal(str(length)),
        width_mm=Decimal(str(width)),
        height_mm=Decimal(str(height)),
        weight_grams=Decimal("100"),
        is_base_unit=True,
        is_active=True,
    )
    db_session.add(pu)
    db_session.commit()
    return pu


def _add_stock(db_session, bin_id, item_id, qty, org_id, batch=None, expiry=None):
    bs = BinStockLevel(
        id=uuid.uuid4(),
        organization_id=org_id,
        bin_location_id=bin_id,
        item_id=item_id,
        quantity_on_hand=Decimal(str(qty)),
        batch_number=batch,
        expiry_date=expiry,
    )
    db_session.add(bs)
    db_session.commit()


class TestPutAway:
    def test_reserved_bin_excluded(
        self, db_session, suggest_service, reservation_service, org_id, warehouse_id
    ):
        b1 = _create_bin(db_session, org_id, warehouse_id, code="B1", capacity=100)
        b2 = _create_bin(db_session, org_id, warehouse_id, code="B2", capacity=100)
        item = _create_item(db_session, org_id)
        worker_a = uuid.uuid4()
        worker_b = uuid.uuid4()

        reservation_service.reserve(bin_id=b1.id, worker_id=worker_a, org_id=org_id)

        result = suggest_service.suggest(
            task_type="put_away",
            item_id=item.id,
            quantity=Decimal("10"),
            warehouse_id=warehouse_id,
            worker_id=worker_b,
            org_id=org_id,
        )
        bin_ids = [s["bin_id"] for s in result["suggestions"]]
        assert b1.id not in bin_ids
        assert b2.id in bin_ids

    def test_excluded_skipped(self, db_session, suggest_service, org_id, warehouse_id):
        b1 = _create_bin(db_session, org_id, warehouse_id, code="B1", capacity=100)
        b2 = _create_bin(db_session, org_id, warehouse_id, code="B2", capacity=100)
        item = _create_item(db_session, org_id)

        result = suggest_service.suggest(
            task_type="put_away",
            item_id=item.id,
            quantity=Decimal("10"),
            warehouse_id=warehouse_id,
            worker_id=uuid.uuid4(),
            org_id=org_id,
            exclude_bin_ids=[b1.id],
        )
        bin_ids = [s["bin_id"] for s in result["suggestions"]]
        assert b1.id not in bin_ids
        assert b2.id in bin_ids

    def test_capacity_insufficient_excluded(
        self, db_session, suggest_service, org_id, warehouse_id
    ):
        # b1 volume (0.005 m³) can't fit 10 units (10 × 0.001 m³ = 0.01 m³).
        b1 = _create_bin(
            db_session, org_id, warehouse_id, code="B1", max_volume_cc=5000
        )
        b2 = _create_bin(
            db_session, org_id, warehouse_id, code="B2", max_volume_cc=100000
        )
        item = _create_item(db_session, org_id)
        _create_packaging_unit(
            db_session, org_id, item.id, length=100, width=100, height=100
        )

        result = suggest_service.suggest(
            task_type="put_away",
            item_id=item.id,
            quantity=Decimal("10"),
            warehouse_id=warehouse_id,
            worker_id=uuid.uuid4(),
            org_id=org_id,
        )
        bin_ids = [s["bin_id"] for s in result["suggestions"]]
        assert b1.id not in bin_ids
        assert b2.id in bin_ids

    def test_consolidation_bonus(
        self, db_session, suggest_service, org_id, warehouse_id
    ):
        b1 = _create_bin(db_session, org_id, warehouse_id, code="B1", capacity=100)
        b2 = _create_bin(db_session, org_id, warehouse_id, code="B2", capacity=100)
        item = _create_item(db_session, org_id)
        _add_stock(db_session, b1.id, item.id, 10, org_id)

        result = suggest_service.suggest(
            task_type="put_away",
            item_id=item.id,
            quantity=Decimal("10"),
            warehouse_id=warehouse_id,
            worker_id=uuid.uuid4(),
            org_id=org_id,
        )
        # B1 has the same item already -> consolidation bonus -> higher score
        assert result["suggestions"][0]["bin_id"] == b1.id
        assert any("same item" in r for r in result["suggestions"][0]["reasons"])

    def test_exclusive_allocation_filter(
        self, db_session, suggest_service, org_id, warehouse_id
    ):
        b1 = _create_bin(db_session, org_id, warehouse_id, code="B1", capacity=100)
        b2 = _create_bin(db_session, org_id, warehouse_id, code="B2", capacity=100)
        item = _create_item(db_session, org_id)
        other_group = uuid.uuid4()
        alloc = LocationAllocation(
            id=uuid.uuid4(),
            organization_id=org_id,
            location_id=b1.id,
            item_group_id=other_group,
            allocation_type="exclusive",
            is_active=True,
        )
        db_session.add(alloc)
        db_session.commit()

        result = suggest_service.suggest(
            task_type="put_away",
            item_id=item.id,
            quantity=Decimal("10"),
            warehouse_id=warehouse_id,
            worker_id=uuid.uuid4(),
            org_id=org_id,
        )
        bin_ids = [s["bin_id"] for s in result["suggestions"]]
        # B1 is exclusively allocated to a different group -> excluded
        assert b1.id not in bin_ids
        assert b2.id in bin_ids

    def test_not_found_item_raises(self, suggest_service, org_id, warehouse_id):
        with pytest.raises(NotFoundError):
            suggest_service.suggest(
                task_type="put_away",
                item_id=uuid.uuid4(),
                quantity=Decimal("1"),
                warehouse_id=warehouse_id,
                worker_id=uuid.uuid4(),
                org_id=org_id,
            )


class TestPick:
    def test_fefo_orders_by_expiry(
        self, db_session, suggest_service, org_id, warehouse_id
    ):
        item = _create_item(db_session, org_id)
        b1 = _create_bin(db_session, org_id, warehouse_id, code="B1")
        b2 = _create_bin(db_session, org_id, warehouse_id, code="B2")
        today = datetime.now(UTC).date()
        _add_stock(
            db_session, b1.id, item.id, 10, org_id, expiry=today + timedelta(days=10)
        )
        _add_stock(
            db_session, b2.id, item.id, 10, org_id, expiry=today + timedelta(days=3)
        )

        result = suggest_service.suggest(
            task_type="pick",
            item_id=item.id,
            quantity=Decimal("5"),
            warehouse_id=warehouse_id,
            worker_id=uuid.uuid4(),
            org_id=org_id,
        )
        # B2 expires sooner -> higher score -> first
        assert result["suggestions"][0]["bin_id"] == b2.id
        assert any("FEFO" in r for r in result["suggestions"][0]["reasons"])

    def test_reserved_bin_excluded_in_pick(
        self, db_session, suggest_service, reservation_service, org_id, warehouse_id
    ):
        item = _create_item(db_session, org_id)
        b1 = _create_bin(db_session, org_id, warehouse_id, code="B1")
        b2 = _create_bin(db_session, org_id, warehouse_id, code="B2")
        _add_stock(db_session, b1.id, item.id, 10, org_id)
        _add_stock(db_session, b2.id, item.id, 10, org_id)
        worker_a = uuid.uuid4()
        reservation_service.reserve(bin_id=b1.id, worker_id=worker_a, org_id=org_id)

        result = suggest_service.suggest(
            task_type="pick",
            item_id=item.id,
            quantity=Decimal("5"),
            warehouse_id=warehouse_id,
            worker_id=uuid.uuid4(),
            org_id=org_id,
        )
        bin_ids = [s["bin_id"] for s in result["suggestions"]]
        assert b1.id not in bin_ids
        assert b2.id in bin_ids

    def test_full_quantity_single_stop_bonus(
        self, db_session, suggest_service, org_id, warehouse_id
    ):
        item = _create_item(db_session, org_id)
        b1 = _create_bin(db_session, org_id, warehouse_id, code="B1")
        b2 = _create_bin(db_session, org_id, warehouse_id, code="B2")
        _add_stock(db_session, b1.id, item.id, 3, org_id)
        _add_stock(db_session, b2.id, item.id, 20, org_id)

        result = suggest_service.suggest(
            task_type="pick",
            item_id=item.id,
            quantity=Decimal("10"),
            warehouse_id=warehouse_id,
            worker_id=uuid.uuid4(),
            org_id=org_id,
        )
        # B2 can satisfy full qty -> single-stop bonus -> higher score
        assert result["suggestions"][0]["bin_id"] == b2.id
        assert any("full quantity" in r for r in result["suggestions"][0]["reasons"])
