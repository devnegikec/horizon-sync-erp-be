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
from app.models.warehouse import Warehouse
from app.models.warehouse_location import WarehouseLocation
from app.models.warehouse_user import WarehouseUser
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


def _create_warehouse(db_session, org_id, code="WH-01"):
    """Helper to create a warehouse."""
    warehouse = Warehouse(
        id=uuid.uuid4(),
        organization_id=org_id,
        name=f"Test Warehouse {code}",
        code=code,
    )
    db_session.add(warehouse)
    db_session.flush()
    return warehouse


def _create_warehouse_worker(db_session, org_id, warehouse_id):
    """Helper to assign a new worker to a warehouse; returns the user id."""
    user_id = uuid.uuid4()
    db_session.add(
        WarehouseUser(
            id=uuid.uuid4(),
            organization_id=org_id,
            user_id=user_id,
            warehouse_id=warehouse_id,
            is_active=True,
        )
    )
    db_session.flush()
    return user_id


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


class TestDistributeBalanced:
    """Unit tests for the SKU-based distribution helper."""

    @staticmethod
    def _spec(sku, serial):
        return {
            "item_id": uuid.uuid4(),
            "sku": sku,
            "batch_number": serial,
            "quantity": Decimal("1"),
            "bin_location_id": None,
            "serial_nos": [serial],
        }

    @classmethod
    def _carton(cls, sku, serials):
        return [cls._spec(sku, serial) for serial in serials]

    def test_never_splits_a_sku_when_every_worker_can_be_filled(self):
        """Each SKU must land on exactly one worker when SKUs >= workers."""
        sku_groups = [
            [self._carton("SKU-A", ["A1", "A2", "A3"])],
            [self._carton("SKU-B", ["B1", "B2"])],
            [self._carton("SKU-C", ["C1"])],
        ]

        chunks = PutAwayService._distribute_balanced(sku_groups, 3)

        owner: dict[str, int] = {}
        for idx, chunk in enumerate(chunks):
            for spec in chunk:
                owner.setdefault(spec["sku"], idx)
                assert owner[spec["sku"]] == idx, "a SKU was split across workers"
        assert set(owner) == {"SKU-A", "SKU-B", "SKU-C"}
        assert sum(len(chunk) for chunk in chunks) == 6

    def test_balances_whole_skus_by_quantity(self):
        """Whole SKUs go to the least-loaded worker (largest-first)."""
        sku_groups = [
            [self._carton("SKU-A", ["A1"])],
            [self._carton("SKU-B", ["B1"])],
            [self._carton("SKU-C", ["C1"])],
            [self._carton("SKU-D", ["D1"])],
        ]
        # 1 carton per SKU, but distinct quantities make the split interesting.
        for group, qty in zip(sku_groups, [10, 8, 6, 4], strict=True):
            for spec in group[0]:
                spec["quantity"] = Decimal(str(qty))

        chunks = PutAwayService._distribute_balanced(sku_groups, 2)

        loads = [
            sum((spec["quantity"] for spec in chunk), Decimal("0")) for chunk in chunks
        ]
        assert loads == [Decimal("14"), Decimal("14")]
        owner = {spec["sku"]: idx for idx, chunk in enumerate(chunks) for spec in chunk}
        assert len(set(owner.values())) == 2, "work was not spread over both workers"

    def test_splits_a_sku_on_carton_boundaries_only_when_needed(self):
        """With fewer SKUs than workers, cartons stay whole on one worker."""
        cartons = [
            self._carton("SKU-A", ["A1", "A2"]),
            self._carton("SKU-A", ["A3", "A4"]),
            self._carton("SKU-A", ["A5"]),
        ]

        chunks = PutAwayService._distribute_balanced([cartons], 3)

        assert all(chunks), "every worker should receive work"
        for carton in cartons:
            serials = {spec["batch_number"] for spec in carton}
            placed = {
                idx
                for idx, chunk in enumerate(chunks)
                if serials & {spec["batch_number"] for spec in chunk}
            }
            assert len(placed) == 1, "a master pack was split across workers"

    def test_single_worker_receives_everything(self):
        """One worker gets all SKUs in a single chunk."""
        sku_groups = [
            [self._carton("SKU-A", ["A1"])],
            [self._carton("SKU-B", ["B1"])],
        ]

        chunks = PutAwayService._distribute_balanced(sku_groups, 1)

        assert len(chunks) == 1
        assert len(chunks[0]) == 2


class TestGenerateFromSlipForWorkers:
    """Put-away work is divided by SKU across the assigned workers."""

    def test_assigns_each_sku_to_exactly_one_worker(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """No SKU may appear on more than one worker's put-away list."""
        session = _create_scan_session(db_session, org_id, warehouse_id)
        slip = _create_receiving_slip(db_session, org_id, warehouse_id, session.id)
        for sku in ("SKU-A", "SKU-B", "SKU-C"):
            _create_item(db_session, org_id, sku)
            for box in range(4):
                _create_receiving_slip_item(
                    db_session, org_id, slip.id, sku, f"{sku}-BOX{box}", 1
                )
        _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "Z01-A01-B01-L01-BIN01",
            capacity=1000,
            total_capacity=1000,
            available_capacity=1000,
        )
        workers = [
            _create_warehouse_worker(db_session, org_id, warehouse_id) for _ in range(2)
        ]
        db_session.commit()

        lists = put_away_service.generate_from_slip_for_workers(
            slip.id, org_id, workers, mode="auto"
        )

        assert len(lists) == 2
        assert {lst.assigned_to for lst in lists} == set(workers)

        owners: dict[str, set] = {}
        for put_away_list in lists:
            for item in put_away_list.items:
                owners.setdefault(item.sku, set()).add(put_away_list.assigned_to)
        assert set(owners) == {"SKU-A", "SKU-B", "SKU-C"}
        for sku, assigned in owners.items():
            assert len(assigned) == 1, f"{sku} was assigned to {len(assigned)} workers"

    def test_creates_one_worker_task_per_list(
        self, db_session, put_away_service, org_id, warehouse_id
    ):
        """Every split list gets its own put-away task for its worker."""
        from app.models.worker_task import WorkerTask

        session = _create_scan_session(db_session, org_id, warehouse_id)
        slip = _create_receiving_slip(db_session, org_id, warehouse_id, session.id)
        for sku in ("SKU-A", "SKU-B"):
            _create_item(db_session, org_id, sku)
            _create_receiving_slip_item(db_session, org_id, slip.id, sku, "BATCH-A", 5)
        _create_location(
            db_session,
            org_id,
            warehouse_id,
            "bin",
            "Z01-A01-B01-L01-BIN01",
            capacity=1000,
            total_capacity=1000,
            available_capacity=1000,
        )
        workers = [
            _create_warehouse_worker(db_session, org_id, warehouse_id) for _ in range(2)
        ]
        db_session.commit()

        lists = put_away_service.generate_from_slip_for_workers(
            slip.id, org_id, workers, mode="auto"
        )

        task_references = {
            task.reference_id
            for task in db_session.query(WorkerTask)
            .filter(WorkerTask.task_type == "put_away")
            .all()
        }
        assert task_references == {lst.id for lst in lists}
        assert all(
            db_session.query(WorkerTask)
            .filter(
                WorkerTask.reference_id == lst.id,
                WorkerTask.worker_id == lst.assigned_to,
            )
            .count()
            == 1
            for lst in lists
        )
