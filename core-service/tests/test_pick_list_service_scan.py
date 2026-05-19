"""Unit tests for PickListService pick scan recording and status transitions.

Tests record_pick_scan, complete_pick_list, and cancel_pick_list methods.
Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 11.1, 11.2, 11.5
"""

import json
import uuid
from decimal import Decimal

import pytest

from app.core.exceptions import ResourceNotFoundException, ValidationError
from app.models.base import PickListStatus
from app.models.bin_stock_level import BinStockLevel
from app.models.pick_list import PickList, PickListItem
from app.models.qr_scan_event import QRScanEvent
from app.models.warehouse_location import WarehouseLocation
from app.services.pick_list_service import PickListService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    return uuid.uuid4()


@pytest.fixture
def worker_id():
    return uuid.uuid4()


@pytest.fixture
def pick_list_service(db_session):
    return PickListService(db_session)


def _create_warehouse(db_session, warehouse_id, org_id):
    """Helper to create a warehouse record for FK constraints."""
    from app.models.warehouse import Warehouse

    wh = Warehouse(
        id=warehouse_id,
        organization_id=org_id,
        name="Test Warehouse",
        code="WH-TEST",
        warehouse_type="warehouse",
    )
    db_session.add(wh)
    db_session.flush()
    return wh


def _create_item(db_session, item_id, org_id, item_code="ITEM-001"):
    """Helper to create an item record."""
    from app.models.item import Item

    item = Item(
        id=item_id,
        organization_id=org_id,
        item_code=item_code,
        item_name=f"Test Item {item_code}",
        item_type="stock",
        uom="Nos",
        maintain_stock=True,
    )
    db_session.add(item)
    db_session.flush()
    return item


def _create_bin_location(
    db_session,
    org_id,
    warehouse_id,
    code="BIN01",
    full_path="Z01-A01-B01-L01-BIN01",
    capacity=1000,
):
    """Helper to create a bin location."""
    loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=org_id,
        warehouse_id=warehouse_id,
        location_type="bin",
        code=code,
        full_path=full_path,
        capacity=Decimal(str(capacity)),
        total_capacity=Decimal(str(capacity)),
        available_capacity=Decimal(str(capacity)),
        position_x=Decimal("0"),
        position_y=Decimal("0"),
        is_active=True,
        version=1,
    )
    db_session.add(loc)
    db_session.flush()
    return loc


def _create_bin_stock(
    db_session, org_id, bin_location_id, item_id, quantity, batch_number=None
):
    """Helper to create a bin stock level record."""
    bsl = BinStockLevel(
        id=uuid.uuid4(),
        organization_id=org_id,
        bin_location_id=bin_location_id,
        item_id=item_id,
        quantity_on_hand=Decimal(str(quantity)),
        batch_number=batch_number,
    )
    db_session.add(bsl)
    db_session.flush()
    return bsl


def _create_stock_level(db_session, org_id, warehouse_id, item_id, on_hand=100):
    """Helper to create a warehouse-level stock level record."""
    from app.models.stock_level import StockLevel

    sl = StockLevel(
        organization_id=org_id,
        product_id=item_id,
        warehouse_id=warehouse_id,
        quantity_on_hand=on_hand,
        quantity_reserved=0,
        quantity_available=on_hand,
    )
    db_session.add(sl)
    db_session.flush()
    return sl


def _create_pick_list_with_item(
    db_session,
    org_id,
    warehouse_id,
    item_id,
    qty=50,
    bin_location_id=None,
    status=PickListStatus.DRAFT,
):
    """Helper to create a pick list with one item."""
    pl = PickList(
        id=uuid.uuid4(),
        organization_id=org_id,
        pick_list_no=f"PL-{uuid.uuid4().hex[:8]}",
        warehouse_id=warehouse_id,
        status=status,
        reference_type="sap_invoice",
        invoice_reference="INV-TEST-001",
    )
    db_session.add(pl)
    db_session.flush()

    pli = PickListItem(
        id=uuid.uuid4(),
        organization_id=org_id,
        pick_list_id=pl.id,
        item_id=item_id,
        warehouse_id=warehouse_id,
        qty=Decimal(str(qty)),
        picked_qty=Decimal("0"),
        uom="Nos",
        bin_location_id=bin_location_id,
        sort_order=1,
    )
    db_session.add(pli)
    db_session.flush()
    db_session.commit()
    db_session.refresh(pl)
    return pl


def _make_qr_payload(sku="ITEM-001", qty=10, batch="BATCH-001", qr_id=None):
    """Helper to create a QR payload JSON string."""
    if qr_id is None:
        qr_id = f"QR-{uuid.uuid4().hex[:8]}"
    return json.dumps(
        {
            "id": qr_id,
            "sku": sku,
            "qty": qty,
            "batch": batch,
        }
    )


class TestRecordPickScan:
    """Tests for record_pick_scan method."""

    def test_records_scan_and_increments_picked_qty(
        self, db_session, pick_list_service, org_id, warehouse_id, worker_id
    ):
        """Should increment picked_qty when a valid scan is recorded."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        bin_loc = _create_bin_location(db_session, org_id, warehouse_id)
        _create_bin_stock(db_session, org_id, bin_loc.id, item_id, 100, "BATCH-001")
        _create_stock_level(db_session, org_id, warehouse_id, item_id, 100)
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session,
            org_id,
            warehouse_id,
            item_id,
            qty=50,
            bin_location_id=bin_loc.id,
        )

        qr_data = _make_qr_payload(sku="ITEM-001", qty=10, batch="BATCH-001")
        result = pick_list_service.record_pick_scan(pl.id, qr_data, worker_id, org_id)

        assert result["picked_qty"] == 10.0
        assert result["remaining_qty"] == 40.0
        assert result["sku"] == "ITEM-001"

    def test_transitions_to_in_progress_on_first_scan(
        self, db_session, pick_list_service, org_id, warehouse_id, worker_id
    ):
        """Should transition pick list from DRAFT to IN_PROGRESS on first scan."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        bin_loc = _create_bin_location(db_session, org_id, warehouse_id)
        _create_bin_stock(db_session, org_id, bin_loc.id, item_id, 100, "BATCH-001")
        _create_stock_level(db_session, org_id, warehouse_id, item_id, 100)
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session,
            org_id,
            warehouse_id,
            item_id,
            qty=50,
            bin_location_id=bin_loc.id,
        )
        assert pl.status == PickListStatus.DRAFT

        qr_data = _make_qr_payload(sku="ITEM-001", qty=5, batch="BATCH-001")
        result = pick_list_service.record_pick_scan(pl.id, qr_data, worker_id, org_id)

        assert result["pick_list_status"] == "in_progress"

    def test_rejects_scan_for_item_not_on_pick_list(
        self, db_session, pick_list_service, org_id, warehouse_id, worker_id
    ):
        """Should reject scan when SKU is not on the pick list."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        other_item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        _create_item(db_session, other_item_id, org_id, "ITEM-999")
        bin_loc = _create_bin_location(db_session, org_id, warehouse_id)
        _create_bin_stock(db_session, org_id, bin_loc.id, item_id, 100)
        _create_stock_level(db_session, org_id, warehouse_id, item_id, 100)
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session,
            org_id,
            warehouse_id,
            item_id,
            qty=50,
            bin_location_id=bin_loc.id,
        )

        # Scan a different item not on the pick list
        qr_data = _make_qr_payload(sku="ITEM-999", qty=5, batch="BATCH-001")
        with pytest.raises(ValidationError, match="not on the pick list"):
            pick_list_service.record_pick_scan(pl.id, qr_data, worker_id, org_id)

    def test_rejects_over_picking(
        self, db_session, pick_list_service, org_id, warehouse_id, worker_id
    ):
        """Should reject scan when scanned qty would exceed required qty."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        bin_loc = _create_bin_location(db_session, org_id, warehouse_id)
        _create_bin_stock(db_session, org_id, bin_loc.id, item_id, 100, "BATCH-001")
        _create_stock_level(db_session, org_id, warehouse_id, item_id, 100)
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session,
            org_id,
            warehouse_id,
            item_id,
            qty=10,
            bin_location_id=bin_loc.id,
        )

        # Try to scan more than required
        qr_data = _make_qr_payload(sku="ITEM-001", qty=15, batch="BATCH-001")
        with pytest.raises(ValidationError, match="Over-picking"):
            pick_list_service.record_pick_scan(pl.id, qr_data, worker_id, org_id)

    def test_decrements_bin_stock_on_scan(
        self, db_session, pick_list_service, org_id, warehouse_id, worker_id
    ):
        """Should decrement bin stock when a pick scan is recorded."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        bin_loc = _create_bin_location(db_session, org_id, warehouse_id)
        bsl = _create_bin_stock(
            db_session, org_id, bin_loc.id, item_id, 100, "BATCH-001"
        )
        _create_stock_level(db_session, org_id, warehouse_id, item_id, 100)
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session,
            org_id,
            warehouse_id,
            item_id,
            qty=50,
            bin_location_id=bin_loc.id,
        )

        qr_data = _make_qr_payload(sku="ITEM-001", qty=10, batch="BATCH-001")
        pick_list_service.record_pick_scan(pl.id, qr_data, worker_id, org_id)

        db_session.refresh(bsl)
        assert bsl.quantity_on_hand == Decimal("90")

    def test_records_scan_event(
        self, db_session, pick_list_service, org_id, warehouse_id, worker_id
    ):
        """Should record a scan event in qr_scan_events table."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        bin_loc = _create_bin_location(db_session, org_id, warehouse_id)
        _create_bin_stock(db_session, org_id, bin_loc.id, item_id, 100, "BATCH-001")
        _create_stock_level(db_session, org_id, warehouse_id, item_id, 100)
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session,
            org_id,
            warehouse_id,
            item_id,
            qty=50,
            bin_location_id=bin_loc.id,
        )

        qr_data = _make_qr_payload(sku="ITEM-001", qty=10, batch="BATCH-001")
        pick_list_service.record_pick_scan(pl.id, qr_data, worker_id, org_id)

        # Check scan event was recorded
        events = (
            db_session.query(QRScanEvent)
            .filter(QRScanEvent.organization_id == org_id)
            .all()
        )
        assert len(events) == 1
        assert events[0].extra_data["scan_context"] == "pick"
        assert events[0].extra_data["pick_list_id"] == str(pl.id)
        assert events[0].extra_data["worker_id"] == str(worker_id)

    def test_rejects_scan_on_completed_pick_list(
        self, db_session, pick_list_service, org_id, warehouse_id, worker_id
    ):
        """Should reject scan on a COMPLETED pick list."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session,
            org_id,
            warehouse_id,
            item_id,
            qty=50,
            status=PickListStatus.COMPLETED,
        )

        qr_data = _make_qr_payload(sku="ITEM-001", qty=5, batch="BATCH-001")
        with pytest.raises(ValidationError, match="Cannot scan items"):
            pick_list_service.record_pick_scan(pl.id, qr_data, worker_id, org_id)

    def test_rejects_scan_on_cancelled_pick_list(
        self, db_session, pick_list_service, org_id, warehouse_id, worker_id
    ):
        """Should reject scan on a CANCELLED pick list."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session,
            org_id,
            warehouse_id,
            item_id,
            qty=50,
            status=PickListStatus.CANCELLED,
        )

        qr_data = _make_qr_payload(sku="ITEM-001", qty=5, batch="BATCH-001")
        with pytest.raises(ValidationError, match="Cannot scan items"):
            pick_list_service.record_pick_scan(pl.id, qr_data, worker_id, org_id)


class TestCompletePickList:
    """Tests for complete_pick_list method."""

    def test_completes_fully_picked_list(
        self, db_session, pick_list_service, org_id, warehouse_id
    ):
        """Should mark pick list as COMPLETED when all items are fully picked."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session,
            org_id,
            warehouse_id,
            item_id,
            qty=10,
            status=PickListStatus.IN_PROGRESS,
        )
        # Manually set picked_qty to match required
        pl.items[0].picked_qty = Decimal("10")
        db_session.commit()

        result = pick_list_service.complete_pick_list(pl.id, org_id)

        assert result.status == PickListStatus.COMPLETED
        assert result.completed_at is not None

    def test_rejects_completion_when_items_not_fully_picked(
        self, db_session, pick_list_service, org_id, warehouse_id
    ):
        """Should reject completion when not all items are fully picked."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session,
            org_id,
            warehouse_id,
            item_id,
            qty=50,
            status=PickListStatus.IN_PROGRESS,
        )
        # picked_qty is 0, required is 50

        with pytest.raises(ValidationError, match="Cannot complete pick list"):
            pick_list_service.complete_pick_list(pl.id, org_id)

    def test_rejects_completion_of_already_completed(
        self, db_session, pick_list_service, org_id, warehouse_id
    ):
        """Should reject completion of an already completed pick list."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session,
            org_id,
            warehouse_id,
            item_id,
            qty=10,
            status=PickListStatus.COMPLETED,
        )

        with pytest.raises(ValidationError, match="Cannot complete pick list"):
            pick_list_service.complete_pick_list(pl.id, org_id)

    def test_raises_not_found_for_invalid_pick_list(
        self, db_session, pick_list_service, org_id
    ):
        """Should raise ResourceNotFoundException for non-existent pick list."""
        with pytest.raises(ResourceNotFoundException):
            pick_list_service.complete_pick_list(uuid.uuid4(), org_id)


class TestCancelPickList:
    """Tests for cancel_pick_list method."""

    def test_cancels_draft_pick_list(
        self, db_session, pick_list_service, org_id, warehouse_id
    ):
        """Should cancel a DRAFT pick list."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session, org_id, warehouse_id, item_id, qty=50
        )

        result = pick_list_service.cancel_pick_list(pl.id, org_id)

        assert result.status == PickListStatus.CANCELLED

    def test_cancels_in_progress_and_releases_stock(
        self, db_session, pick_list_service, org_id, warehouse_id
    ):
        """Should cancel IN_PROGRESS pick list and release reserved stock back to bins."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        bin_loc = _create_bin_location(db_session, org_id, warehouse_id)
        bsl = _create_bin_stock(db_session, org_id, bin_loc.id, item_id, 80)
        _create_stock_level(db_session, org_id, warehouse_id, item_id, 80)
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session,
            org_id,
            warehouse_id,
            item_id,
            qty=50,
            bin_location_id=bin_loc.id,
            status=PickListStatus.IN_PROGRESS,
        )
        # Simulate that 20 units were already picked
        pl.items[0].picked_qty = Decimal("20")
        db_session.commit()

        result = pick_list_service.cancel_pick_list(pl.id, org_id)

        assert result.status == PickListStatus.CANCELLED
        # picked_qty should be reset to 0
        assert result.items[0].picked_qty == Decimal("0")
        # Bin stock should be restored (80 + 20 = 100)
        db_session.refresh(bsl)
        assert bsl.quantity_on_hand == Decimal("100")

    def test_rejects_cancel_of_completed_pick_list(
        self, db_session, pick_list_service, org_id, warehouse_id
    ):
        """Should reject cancellation of a completed pick list."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session,
            org_id,
            warehouse_id,
            item_id,
            qty=10,
            status=PickListStatus.COMPLETED,
        )

        with pytest.raises(ValidationError, match="Cannot cancel a completed"):
            pick_list_service.cancel_pick_list(pl.id, org_id)

    def test_rejects_cancel_of_already_cancelled(
        self, db_session, pick_list_service, org_id, warehouse_id
    ):
        """Should reject cancellation of an already cancelled pick list."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "ITEM-001")
        db_session.commit()

        pl = _create_pick_list_with_item(
            db_session,
            org_id,
            warehouse_id,
            item_id,
            qty=10,
            status=PickListStatus.CANCELLED,
        )

        with pytest.raises(ValidationError, match="already cancelled"):
            pick_list_service.cancel_pick_list(pl.id, org_id)

    def test_raises_not_found_for_invalid_pick_list(
        self, db_session, pick_list_service, org_id
    ):
        """Should raise ResourceNotFoundException for non-existent pick list."""
        with pytest.raises(ResourceNotFoundException):
            pick_list_service.cancel_pick_list(uuid.uuid4(), org_id)
