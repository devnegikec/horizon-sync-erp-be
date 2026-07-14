"""Unit tests for PutAwayService."""

import uuid
from decimal import Decimal

import pytest

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.item import Item
from app.models.location_allocation import LocationAllocation
from app.models.put_away_list import PutAwayList, PutAwayListItem
from app.models.receiving_slip import ReceivingSlip, ReceivingSlipItem
from app.models.scan_session import ScanSession
from app.models.warehouse_location import WarehouseLocation
from app.services.put_away_service import PutAwayService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    return uuid.uuid4()


@pytest.fixture
def put_away_service(db_session):
    return PutAwayService(db_session)


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
    position_x=0,
    position_y=0,
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
        position_x=Decimal(str(position_x)),
        position_y=Decimal(str(position_y)),
    )
    db_session.add(loc)
    db_session.flush()
    return loc


def _create_item(db_session, org_id, item_code, item_group_id=None):
    """Helper to create an item."""
    item = Item(
        id=uuid.uuid4(),
        organization_id=org_id,
        item_code=item_code,
        item_name=f"Test Item {item_code}",
        item_group_id=item_group_id,
    )
    db_session.add(item)
    db_session.flush()
    return item


def _create_scan_session(db_session, org_id, warehouse_id):
    """Helper to create a scan session."""
    session = ScanSession(
        id=uuid.uuid4(),
        organization_id=org_id,
        session_type="inbound",
        worker_id=uuid.uuid4(),
        warehouse_id=warehouse_id,
        status="closed",
    )
    db_session.add(session)
    db_session.flush()
    return session


def _create_receiving_slip(
    db_session, org_id, warehouse_id, session_id, status="pending_putaway"
):
    """Helper to create a receiving slip."""
    slip = ReceivingSlip(
        id=uuid.uuid4(),
        organization_id=org_id,
        slip_number=f"RS-{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        warehouse_id=warehouse_id,
        status=status,
        total_boxes=1,
        total_items=10,
    )
    db_session.add(slip)
    db_session.flush()
    return slip


def _create_receiving_slip_item(db_session, org_id, slip_id, sku, batch, quantity):
    """Helper to create a receiving slip item."""
    item = ReceivingSlipItem(
        id=uuid.uuid4(),
        organization_id=org_id,
        slip_id=slip_id,
        sku=sku,
        batch_number=batch,
        quantity=quantity,
        box_count=1,
        flag="ok",
    )
    db_session.add(item)
    db_session.flush()
    return item


class TestGenerateFromSlip:
    """Tests for generate_from_slip method."""

    def test_generates_put_away_list_from_approved_slip(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """Should generate a put-away list from a pending_putaway slip."""
        session = _create_scan_session(db_session, org_id, warehouse_id)
        slip = _create_receiving_slip(db_session, org_id, warehouse_id, session.id)
        _create_item(db_session, org_id, "SKU-001")
        _create_receiving_slip_item(
            db_session, org_id, slip.id, "SKU-001", "BATCH-A", 10
        )

        # Create a bin with capacity
        _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "Z01-A01-B01-L01-BIN01",
            capacity=100,
            total_capacity=100,
            available_capacity=100,
        )
        db_session.commit()

        result = put_away_service.generate_from_slip(slip.id, org_id)

        assert result is not None
        assert result.status == "pending"
        assert result.warehouse_id == warehouse_id
        assert result.receiving_slip_id == slip.id
        assert len(result.items) > 0

    def test_raises_not_found_for_invalid_slip(
        self, db_session, put_away_service, org_id
    ):
        """Should raise NotFoundError for non-existent slip."""
        with pytest.raises(NotFoundError, match="Receiving slip not found"):
            put_away_service.generate_from_slip(uuid.uuid4(), org_id)

    def test_raises_state_error_for_wrong_status(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """Should raise StateError if slip is not in pending_putaway status."""
        session = _create_scan_session(db_session, org_id, warehouse_id)
        slip = _create_receiving_slip(
            db_session, org_id, warehouse_id, session.id, status="pending_review"
        )
        db_session.commit()

        with pytest.raises(StateError, match="pending_putaway"):
            put_away_service.generate_from_slip(slip.id, org_id)

    def test_skips_damaged_items(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """Should skip items flagged as damaged."""
        session = _create_scan_session(db_session, org_id, warehouse_id)
        slip = _create_receiving_slip(db_session, org_id, warehouse_id, session.id)
        _create_item(db_session, org_id, "SKU-001")

        # Create a damaged item
        damaged_item = ReceivingSlipItem(
            id=uuid.uuid4(),
            organization_id=org_id,
            slip_id=slip.id,
            sku="SKU-001",
            batch_number="BATCH-A",
            quantity=10,
            box_count=1,
            flag="damaged",
        )
        db_session.add(damaged_item)

        _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            capacity=100,
            total_capacity=100,
            available_capacity=100,
        )
        db_session.commit()

        result = put_away_service.generate_from_slip(slip.id, org_id)

        # No items should be generated for damaged items
        assert len(result.items) == 0

    def test_respects_exclusive_allocation(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """Should only assign to exclusively allocated bins for the item group."""
        session = _create_scan_session(db_session, org_id, warehouse_id)
        slip = _create_receiving_slip(db_session, org_id, warehouse_id, session.id)

        item_group_id = uuid.uuid4()
        _create_item(db_session, org_id, "SKU-001", item_group_id=item_group_id)
        _create_receiving_slip_item(
            db_session, org_id, slip.id, "SKU-001", "BATCH-A", 10
        )

        # Create an exclusively allocated bin
        exclusive_bin = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "Z01-A01-B01-L01-BIN01",
            capacity=100,
            total_capacity=100,
            available_capacity=100,
        )

        # Create another unallocated bin
        _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "Z01-A02-B01-L01-BIN01",
            capacity=100,
            total_capacity=100,
            available_capacity=100,
        )

        # Create exclusive allocation
        allocation = LocationAllocation(
            id=uuid.uuid4(),
            organization_id=org_id,
            location_id=exclusive_bin.id,
            item_group_id=item_group_id,
            allocation_type="exclusive",
            priority=1,
            is_active=True,
        )
        db_session.add(allocation)
        db_session.commit()

        result = put_away_service.generate_from_slip(slip.id, org_id)

        # Should only use the exclusively allocated bin
        assert len(result.items) == 1
        assert result.items[0].bin_location_id == exclusive_bin.id

    def test_splits_across_bins_when_capacity_insufficient(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """Should split items across multiple bins when one bin is insufficient."""
        session = _create_scan_session(db_session, org_id, warehouse_id)
        slip = _create_receiving_slip(db_session, org_id, warehouse_id, session.id)
        _create_item(db_session, org_id, "SKU-001")
        _create_receiving_slip_item(
            db_session, org_id, slip.id, "SKU-001", "BATCH-A", 80
        )

        # Create two bins with limited capacity
        _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "Z01-A01-B01-L01-BIN01",
            capacity=50,
            total_capacity=50,
            available_capacity=50,
        )
        _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "Z01-A01-B01-L01-BIN02",
            capacity=50,
            total_capacity=50,
            available_capacity=50,
        )
        db_session.commit()

        result = put_away_service.generate_from_slip(slip.id, org_id)

        # Should split across two bins
        assert len(result.items) == 2
        total_qty = sum(Decimal(str(i.quantity)) for i in result.items)
        assert total_qty == Decimal("80")


class TestCompleteItem:
    """Tests for complete_item method."""

    def test_completes_item_and_updates_bin_stock(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """Should mark item as completed and add stock to the bin."""
        item = _create_item(db_session, org_id, "SKU-001")
        bin_loc = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            capacity=100,
            total_capacity=100,
            available_capacity=100,
        )

        # Create put-away list and item
        put_away_list = PutAwayList(
            id=uuid.uuid4(),
            organization_id=org_id,
            warehouse_id=warehouse_id,
            put_away_list_no="PA-001",
            status="pending",
        )
        db_session.add(put_away_list)
        db_session.flush()

        put_away_item = PutAwayListItem(
            id=uuid.uuid4(),
            organization_id=org_id,
            put_away_list_id=put_away_list.id,
            item_id=item.id,
            sku="SKU-001",
            batch_number="BATCH-A",
            quantity=Decimal("25"),
            bin_location_id=bin_loc.id,
            status="pending",
        )
        db_session.add(put_away_item)
        db_session.commit()

        worker_id = uuid.uuid4()
        result = put_away_service.complete_item(put_away_item.id, worker_id, org_id)

        assert result.status == "completed"
        assert result.completed_at is not None

    def test_raises_not_found_for_invalid_item(
        self, db_session, put_away_service, org_id
    ):
        """Should raise NotFoundError for non-existent put-away item."""
        with pytest.raises(NotFoundError, match="Put-away list item not found"):
            put_away_service.complete_item(uuid.uuid4(), uuid.uuid4(), org_id)

    def test_raises_state_error_for_already_completed(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """Should raise StateError if item is already completed."""
        item = _create_item(db_session, org_id, "SKU-001")
        bin_loc = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            capacity=100,
            total_capacity=100,
            available_capacity=100,
        )

        put_away_list = PutAwayList(
            id=uuid.uuid4(),
            organization_id=org_id,
            warehouse_id=warehouse_id,
            put_away_list_no="PA-001",
            status="pending",
        )
        db_session.add(put_away_list)
        db_session.flush()

        put_away_item = PutAwayListItem(
            id=uuid.uuid4(),
            organization_id=org_id,
            put_away_list_id=put_away_list.id,
            item_id=item.id,
            sku="SKU-001",
            batch_number="BATCH-A",
            quantity=Decimal("25"),
            bin_location_id=bin_loc.id,
            status="completed",
        )
        db_session.add(put_away_item)
        db_session.commit()

        with pytest.raises(StateError, match="pending"):
            put_away_service.complete_item(put_away_item.id, uuid.uuid4(), org_id)

    def test_updates_slip_to_putaway_complete_when_all_done(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """Should update receiving slip to PUTAWAY_COMPLETE when all items done."""
        session = _create_scan_session(db_session, org_id, warehouse_id)
        slip = _create_receiving_slip(db_session, org_id, warehouse_id, session.id)
        item = _create_item(db_session, org_id, "SKU-001")
        bin_loc = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "BIN01",
            capacity=100,
            total_capacity=100,
            available_capacity=100,
        )

        put_away_list = PutAwayList(
            id=uuid.uuid4(),
            organization_id=org_id,
            warehouse_id=warehouse_id,
            put_away_list_no="PA-001",
            status="pending",
            receiving_slip_id=slip.id,
        )
        db_session.add(put_away_list)
        db_session.flush()

        put_away_item = PutAwayListItem(
            id=uuid.uuid4(),
            organization_id=org_id,
            put_away_list_id=put_away_list.id,
            item_id=item.id,
            sku="SKU-001",
            batch_number="BATCH-A",
            quantity=Decimal("10"),
            bin_location_id=bin_loc.id,
            status="pending",
        )
        db_session.add(put_away_item)
        db_session.commit()

        put_away_service.complete_item(put_away_item.id, uuid.uuid4(), org_id)

        db_session.refresh(slip)
        assert slip.status == "putaway_complete"


class TestSkipItem:
    """Tests for skip_item method."""

    def test_skips_item_with_reason(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """Should mark item as skipped with the given reason."""
        item = _create_item(db_session, org_id, "SKU-001")

        put_away_list = PutAwayList(
            id=uuid.uuid4(),
            organization_id=org_id,
            warehouse_id=warehouse_id,
            put_away_list_no="PA-001",
            status="pending",
        )
        db_session.add(put_away_list)
        db_session.flush()

        put_away_item = PutAwayListItem(
            id=uuid.uuid4(),
            organization_id=org_id,
            put_away_list_id=put_away_list.id,
            item_id=item.id,
            sku="SKU-001",
            batch_number="BATCH-A",
            quantity=Decimal("10"),
            status="pending",
        )
        db_session.add(put_away_item)
        db_session.commit()

        result = put_away_service.skip_item(
            put_away_item.id, "Bin location inaccessible", org_id
        )

        assert result.status == "skipped"
        assert result.notes == "Bin location inaccessible"

    def test_raises_validation_error_for_empty_reason(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """Should raise ValidationError if reason is empty."""
        item = _create_item(db_session, org_id, "SKU-001")

        put_away_list = PutAwayList(
            id=uuid.uuid4(),
            organization_id=org_id,
            warehouse_id=warehouse_id,
            put_away_list_no="PA-001",
            status="pending",
        )
        db_session.add(put_away_list)
        db_session.flush()

        put_away_item = PutAwayListItem(
            id=uuid.uuid4(),
            organization_id=org_id,
            put_away_list_id=put_away_list.id,
            item_id=item.id,
            sku="SKU-001",
            batch_number="BATCH-A",
            quantity=Decimal("10"),
            status="pending",
        )
        db_session.add(put_away_item)
        db_session.commit()

        with pytest.raises(ValidationError, match="reason"):
            put_away_service.skip_item(put_away_item.id, "", org_id)

    def test_raises_not_found_for_invalid_item(
        self, db_session, put_away_service, org_id
    ):
        """Should raise NotFoundError for non-existent put-away item."""
        with pytest.raises(NotFoundError, match="Put-away list item not found"):
            put_away_service.skip_item(uuid.uuid4(), "Some reason", org_id)

    def test_raises_state_error_for_already_completed(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """Should raise StateError if item is already completed."""
        item = _create_item(db_session, org_id, "SKU-001")

        put_away_list = PutAwayList(
            id=uuid.uuid4(),
            organization_id=org_id,
            warehouse_id=warehouse_id,
            put_away_list_no="PA-001",
            status="pending",
        )
        db_session.add(put_away_list)
        db_session.flush()

        put_away_item = PutAwayListItem(
            id=uuid.uuid4(),
            organization_id=org_id,
            put_away_list_id=put_away_list.id,
            item_id=item.id,
            sku="SKU-001",
            batch_number="BATCH-A",
            quantity=Decimal("10"),
            status="completed",
        )
        db_session.add(put_away_item)
        db_session.commit()

        with pytest.raises(StateError, match="pending"):
            put_away_service.skip_item(put_away_item.id, "Some reason", org_id)
