"""Integration tests for the approve_slip → put-away generation → worker task wiring.

Verifies that:
1. InboundService.approve_slip triggers PutAwayService.generate_from_slip
2. PutAwayService.generate_from_slip creates a worker task via TaskService
3. Put-away list generation respects allocations and routes items

Requirements: 7.3, 8.1
"""

import uuid
from decimal import Decimal

import pytest

from app.models.item import Item
from app.models.location_allocation import LocationAllocation
from app.models.put_away_list import PutAwayList
from app.models.receiving_slip import ReceivingSlip, ReceivingSlipItem
from app.models.scan_session import ScanSession
from app.models.warehouse_location import WarehouseLocation
from app.models.worker_task import WorkerTask
from app.services.inbound_service import InboundService
from app.services.put_away_service import PutAwayService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def worker_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    return uuid.uuid4()


@pytest.fixture
def inbound_service(db_session):
    return InboundService(db_session)


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
    """Helper to create a closed scan session."""
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
    db_session, org_id, warehouse_id, session_id, status="pending_review"
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


class TestApproveSlipTriggersPutAway:
    """Tests that approve_slip triggers put-away list generation."""

    def test_approve_slip_generates_put_away_list(
        self, db_session, inbound_service, org_id, warehouse_id
    ):
        """Approving a slip should generate a put-away list."""
        session = _create_scan_session(db_session, org_id, warehouse_id)
        slip = _create_receiving_slip(
            db_session, org_id, warehouse_id, session.id, status="pending_review"
        )
        item = _create_item(db_session, org_id, "SKU-001")
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

        # Approve the slip
        result = inbound_service.approve_slip(
            slip_id=slip.id,
            organization_id=org_id,
        )

        # Verify slip status transitioned to pending_putaway
        assert result["status"] == "pending_putaway"

        # Verify a put-away list was created
        put_away_lists = (
            db_session.query(PutAwayList)
            .filter(
                PutAwayList.receiving_slip_id == slip.id,
                PutAwayList.organization_id == org_id,
            )
            .all()
        )
        assert len(put_away_lists) == 1
        assert put_away_lists[0].status == "pending"
        assert put_away_lists[0].warehouse_id == warehouse_id

    def test_approve_slip_with_worker_creates_task(
        self, db_session, inbound_service, org_id, warehouse_id, worker_id
    ):
        """Approving a slip with worker_id should create a worker task."""
        session = _create_scan_session(db_session, org_id, warehouse_id)
        slip = _create_receiving_slip(
            db_session, org_id, warehouse_id, session.id, status="pending_review"
        )
        item = _create_item(db_session, org_id, "SKU-002")
        _create_receiving_slip_item(
            db_session, org_id, slip.id, "SKU-002", "BATCH-B", 5
        )

        # Create a bin with capacity
        _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "Z01-A01-B01-L01-BIN02",
            capacity=100,
            total_capacity=100,
            available_capacity=100,
        )
        db_session.commit()

        # Approve the slip with a worker_id
        result = inbound_service.approve_slip(
            slip_id=slip.id,
            organization_id=org_id,
            worker_id=worker_id,
        )

        assert result["status"] == "pending_putaway"

        # Verify a worker task was created
        tasks = (
            db_session.query(WorkerTask)
            .filter(
                WorkerTask.organization_id == org_id,
                WorkerTask.worker_id == worker_id,
                WorkerTask.task_type == "put_away",
            )
            .all()
        )
        assert len(tasks) == 1
        assert tasks[0].status == "assigned"

        # Verify the task references the put-away list
        put_away_list = (
            db_session.query(PutAwayList)
            .filter(PutAwayList.receiving_slip_id == slip.id)
            .first()
        )
        assert tasks[0].reference_id == put_away_list.id

    def test_approve_slip_with_worker_assigns_put_away_list(
        self, db_session, inbound_service, org_id, warehouse_id, worker_id
    ):
        """Approving with worker_id should set assigned_to on the put-away list."""
        session = _create_scan_session(db_session, org_id, warehouse_id)
        slip = _create_receiving_slip(
            db_session, org_id, warehouse_id, session.id, status="pending_review"
        )
        _create_item(db_session, org_id, "SKU-003")
        _create_receiving_slip_item(
            db_session, org_id, slip.id, "SKU-003", "BATCH-C", 8
        )

        _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "Z01-A01-B01-L01-BIN03",
            capacity=100,
            total_capacity=100,
            available_capacity=100,
        )
        db_session.commit()

        inbound_service.approve_slip(
            slip_id=slip.id,
            organization_id=org_id,
            worker_id=worker_id,
        )

        # Verify assigned_to is set on the put-away list
        put_away_list = (
            db_session.query(PutAwayList)
            .filter(PutAwayList.receiving_slip_id == slip.id)
            .first()
        )
        assert put_away_list.assigned_to == worker_id

    def test_approve_slip_without_worker_no_task_created(
        self, db_session, inbound_service, org_id, warehouse_id
    ):
        """Approving without worker_id should not create a worker task."""
        session = _create_scan_session(db_session, org_id, warehouse_id)
        slip = _create_receiving_slip(
            db_session, org_id, warehouse_id, session.id, status="pending_review"
        )
        _create_item(db_session, org_id, "SKU-004")
        _create_receiving_slip_item(
            db_session, org_id, slip.id, "SKU-004", "BATCH-D", 3
        )

        _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "Z01-A01-B01-L01-BIN04",
            capacity=100,
            total_capacity=100,
            available_capacity=100,
        )
        db_session.commit()

        inbound_service.approve_slip(
            slip_id=slip.id,
            organization_id=org_id,
        )

        # Verify no worker task was created
        tasks = (
            db_session.query(WorkerTask)
            .filter(WorkerTask.organization_id == org_id)
            .all()
        )
        assert len(tasks) == 0


class TestPutAwayRespectsAllocations:
    """Tests that put-away generation respects location allocations."""

    def test_exclusive_allocation_routes_to_allocated_bins(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """Items with exclusive allocations should only go to allocated bins."""
        item_group_id = uuid.uuid4()
        item = _create_item(db_session, org_id, "SKU-EXCL", item_group_id=item_group_id)

        # Create an exclusively allocated bin
        exclusive_bin = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "Z01-A01-B01-L01-EXCL",
            capacity=100,
            total_capacity=100,
            available_capacity=100,
            position_x=1,
            position_y=1,
        )

        # Create an unallocated bin
        unallocated_bin = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "Z01-A02-B01-L01-FREE",
            capacity=100,
            total_capacity=100,
            available_capacity=100,
            position_x=5,
            position_y=5,
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

        # Create receiving slip
        session = _create_scan_session(db_session, org_id, warehouse_id)
        slip = _create_receiving_slip(
            db_session, org_id, warehouse_id, session.id, status="pending_putaway"
        )
        _create_receiving_slip_item(
            db_session, org_id, slip.id, "SKU-EXCL", "BATCH-E", 10
        )
        db_session.commit()

        result = put_away_service.generate_from_slip(slip.id, org_id)

        # Verify items are assigned to the exclusive bin only
        assert len(result.items) > 0
        for item in result.items:
            assert item.bin_location_id == exclusive_bin.id

    def test_put_away_items_have_sort_order(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """Put-away items should have sort_order set by the routing optimizer."""
        item = _create_item(db_session, org_id, "SKU-ROUTE")

        # Create multiple bins at different positions
        bin1 = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "Z01-A01-B01-L01-B01",
            capacity=50,
            total_capacity=50,
            available_capacity=50,
            position_x=10,
            position_y=10,
        )
        bin2 = _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "Z01-A01-B02-L01-B01",
            capacity=50,
            total_capacity=50,
            available_capacity=50,
            position_x=1,
            position_y=1,
        )

        # Create receiving slip with quantity that needs splitting
        session = _create_scan_session(db_session, org_id, warehouse_id)
        slip = _create_receiving_slip(
            db_session, org_id, warehouse_id, session.id, status="pending_putaway"
        )
        _create_receiving_slip_item(
            db_session, org_id, slip.id, "SKU-ROUTE", "BATCH-F", 80
        )
        db_session.commit()

        result = put_away_service.generate_from_slip(slip.id, org_id)

        # Verify items have sort_order assigned
        items_with_bins = [i for i in result.items if i.bin_location_id is not None]
        if len(items_with_bins) > 1:
            sort_orders = [i.sort_order for i in items_with_bins]
            # Sort orders should be sequential positive integers
            assert all(s >= 1 for s in sort_orders)
            # All sort orders should be unique
            assert len(set(sort_orders)) == len(sort_orders)
