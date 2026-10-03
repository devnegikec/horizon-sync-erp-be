"""Unit tests for ScannedItemTrackingService — dual-axis state machine."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.item import Item
from app.models.put_away_list import PutAwayList, PutAwayListItem
from app.models.receiving_slip import ReceivingSlip
from app.models.scan_session import ScanSession, ScanSessionItem
from app.models.scanned_item_tracking import ScannedItemTracking
from app.models.warehouse_location import WarehouseLocation
from app.services.scanned_item_tracking_service import (
    ScannedItemTrackingService,
)


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    return uuid.uuid4()


@pytest.fixture
def svc(db_session):
    return ScannedItemTrackingService(db_session)


def _create_warehouse(db_session, org_id, wh_id):
    from app.models.warehouse import Warehouse
    wh = Warehouse(
        id=wh_id, organization_id=org_id, name="Test WH", code="WH-001",
        warehouse_type="warehouse",
    )
    db_session.add(wh)
    db_session.flush()
    return wh


def _create_item(db_session, org_id):
    item = Item(
        id=uuid.uuid4(), organization_id=org_id,
        item_name="Test Item", item_code="ITM-001", sku="SKU-001",
        item_type="stock", uom="pcs",
    )
    db_session.add(item)
    db_session.flush()
    return item


def _create_bin(db_session, org_id, wh_id):
    loc = WarehouseLocation(
        id=uuid.uuid4(), organization_id=org_id, warehouse_id=wh_id,
        location_type="bin", code="BIN-A-01", capacity=100,
    )
    db_session.add(loc)
    db_session.flush()
    return loc


def _create_session(db_session, org_id, wh_id):
    session = ScanSession(
        id=uuid.uuid4(), organization_id=org_id, warehouse_id=wh_id,
        status="open", session_type="inbound", worker_id=uuid.uuid4(),
    )
    db_session.add(session)
    db_session.flush()
    return session


def _create_tracking(db_session, org_id, wh_id, session, item, qr="QR-001"):
    scan_item = ScanSessionItem(
        id=uuid.uuid4(), organization_id=org_id,
        session_id=session.id, qr_identifier=qr, sku=item.sku,
        raw_quantity=10,
    )
    db_session.add(scan_item)
    db_session.flush()

    tracking = ScannedItemTracking(
        organization_id=org_id, warehouse_id=wh_id,
        scan_session_id=session.id, scan_session_item_id=scan_item.id,
        qr_identifier=qr, item_id=item.id, sku=item.sku,
        quantity=10, receiving_status="scanned", putaway_status="pending",
        stock_entered=False,
    )
    db_session.add(tracking)
    db_session.flush()
    return tracking


# ═══════════════════════════════════════════════════════════════════════════
# Gate Function Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestGateFunctions:
    def test_can_scan_new_qr(self, db_session, svc, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        session = _create_session(db_session, org_id, warehouse_id)
        assert svc.can_scan("NEW-QR", session.id) is True

    def test_can_scan_duplicate_rejected(self, db_session, svc, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        _create_tracking(db_session, org_id, warehouse_id, session, item, "QR-001")
        assert svc.can_scan("QR-001", session.id) is False

    def test_can_put_away_ready(self, db_session, svc, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        _create_tracking(db_session, org_id, warehouse_id, session, item, "QR-001")
        ok, err = svc.can_put_away("QR-001")
        assert ok is True
        assert err is None

    def test_can_put_away_not_scanned(self, svc):
        ok, err = svc.can_put_away("NONEXISTENT")
        assert ok is False
        assert "Not scanned" in err

    def test_can_put_away_already_binned(self, db_session, svc, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        t = _create_tracking(db_session, org_id, warehouse_id, session, item, "QR-002")
        t.putaway_status = "completed"
        db_session.flush()
        ok, err = svc.can_put_away("QR-002")
        assert ok is False
        assert "Already put away" in err

    def test_can_put_away_rejected(self, db_session, svc, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        t = _create_tracking(db_session, org_id, warehouse_id, session, item, "QR-003")
        t.receiving_status = "rejected"
        db_session.flush()
        ok, err = svc.can_put_away("QR-003")
        assert ok is False
        assert "Rejected" in err

    def test_can_approve_scanned(self, db_session, svc, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        t = _create_tracking(db_session, org_id, warehouse_id, session, item)
        ok, err = svc.can_approve(t)
        assert ok is True

    def test_can_approve_already_approved(self, db_session, svc, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        t = _create_tracking(db_session, org_id, warehouse_id, session, item)
        t.receiving_status = "approved"
        ok, err = svc.can_approve(t)
        assert ok is False
        assert "Already approved" in err


# ═══════════════════════════════════════════════════════════════════════════
# Tracking Creation Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestTrackingCreation:
    def test_create_from_scan(self, db_session, svc, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        scan_item = ScanSessionItem(
            id=uuid.uuid4(), organization_id=org_id,
            session_id=session.id, qr_identifier="QR-NEW", sku=item.sku,
            raw_quantity=5,
        )
        db_session.add(scan_item)
        db_session.flush()

        t = svc.create_from_scan(
            organization_id=org_id, warehouse_id=warehouse_id,
            session_id=session.id, scan_item_id=scan_item.id,
            qr_identifier="QR-NEW", item_id=item.id, sku=item.sku,
            quantity=5, batch_number="BATCH-01", scanned_by=uuid.uuid4(),
        )

        assert t.receiving_status == "scanned"
        assert t.putaway_status == "pending"
        assert t.stock_entered is False
        assert t.qr_identifier == "QR-NEW"


# ═══════════════════════════════════════════════════════════════════════════
# Dual-Axis State Machine Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDualAxis:
    def test_stock_not_entered_when_only_scanned(self, db_session, svc, org_id, warehouse_id):
        """Stock should NOT enter when receiving=scanned, putaway=pending."""
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        t = _create_tracking(db_session, org_id, warehouse_id, session, item)
        assert t.receiving_status == "scanned"
        assert t.putaway_status == "pending"
        assert t.stock_entered is False

    def test_stock_not_entered_putaway_only(self, db_session, svc, org_id, warehouse_id):
        """Stock should NOT enter when receiving=scanned, putaway=completed."""
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        t = _create_tracking(db_session, org_id, warehouse_id, session, item)
        t.putaway_status = "completed"
        db_session.flush()
        assert t.stock_entered is False

    def test_stock_not_entered_approval_only(self, db_session, svc, org_id, warehouse_id):
        """Stock should NOT enter when receiving=approved, putaway=pending."""
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        t = _create_tracking(db_session, org_id, warehouse_id, session, item)
        t.receiving_status = "approved"
        db_session.flush()
        assert t.stock_entered is False

    def test_should_enter_stock_both_complete(self, db_session, svc, org_id, warehouse_id):
        """Stock should enter when BOTH receiving=approved AND putaway=completed."""
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        t = _create_tracking(db_session, org_id, warehouse_id, session, item)
        t.receiving_status = "approved"
        t.putaway_status = "completed"
        assert svc._ScannedItemTrackingService__should_enter_stock(t) is True

    def test_should_not_enter_stock_already_entered(self, db_session, svc, org_id, warehouse_id):
        """should_enter_stock returns False when stock_entered is already True."""
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        t = _create_tracking(db_session, org_id, warehouse_id, session, item)
        t.receiving_status = "approved"
        t.putaway_status = "completed"
        t.stock_entered = True
        assert svc._ScannedItemTrackingService__should_enter_stock(t) is False


# ═══════════════════════════════════════════════════════════════════════════
# Complete Put-Away Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestCompletePutaway:
    def test_complete_putaway_updates_status(self, db_session, svc, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        bin_loc = _create_bin(db_session, org_id, warehouse_id)
        session = _create_session(db_session, org_id, warehouse_id)
        _create_tracking(db_session, org_id, warehouse_id, session, item, "QR-PA")

        user_id = uuid.uuid4()
        t = svc.complete_putaway(
            qr_identifier="QR-PA", bin_location_id=bin_loc.id,
            putaway_by=user_id,
        )

        assert t.putaway_status == "completed"
        assert t.bin_location_id == bin_loc.id
        assert t.putaway_by == user_id

    def test_complete_putaway_nonexistent_qr(self, svc):
        with pytest.raises(ValueError, match="No tracking found"):
            svc.complete_putaway(
                qr_identifier="NOPE", bin_location_id=uuid.uuid4(),
                putaway_by=uuid.uuid4(),
            )

    def test_complete_putaway_already_binned_raises(self, db_session, svc, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        t = _create_tracking(db_session, org_id, warehouse_id, session, item, "QR-DONE")
        t.putaway_status = "completed"
        db_session.flush()

        with pytest.raises(ValueError, match="Already put away"):
            svc.complete_putaway(
                qr_identifier="QR-DONE", bin_location_id=uuid.uuid4(),
                putaway_by=uuid.uuid4(),
            )


# ═══════════════════════════════════════════════════════════════════════════
# Approval Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestApproval:
    def test_approve_items_enters_stock_when_putaway_done(self, db_session, svc, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        bin_loc = _create_bin(db_session, org_id, warehouse_id)
        session = _create_session(db_session, org_id, warehouse_id)
        t = _create_tracking(db_session, org_id, warehouse_id, session, item, "QR-APPR")

        # Link to a slip
        slip = ReceivingSlip(
            id=uuid.uuid4(), organization_id=org_id, warehouse_id=warehouse_id,
            status="pending_review", session_id=session.id,
        )
        db_session.add(slip)
        db_session.flush()
        t.receiving_slip_id = slip.id
        t.putaway_status = "completed"
        t.bin_location_id = bin_loc.id
        db_session.flush()

        count = svc.approve_items(slip.id, approved_by=uuid.uuid4())

        db_session.refresh(t)
        assert t.receiving_status == "approved"
        assert t.stock_entered is True
        assert count >= 1

    def test_approve_items_no_stock_when_putaway_pending(self, db_session, svc, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        t = _create_tracking(db_session, org_id, warehouse_id, session, item, "QR-NO-PA")

        slip = ReceivingSlip(
            id=uuid.uuid4(), organization_id=org_id, warehouse_id=warehouse_id,
            status="pending_review", session_id=session.id,
        )
        db_session.add(slip)
        db_session.flush()
        t.receiving_slip_id = slip.id
        db_session.flush()

        count = svc.approve_items(slip.id, approved_by=uuid.uuid4())

        db_session.refresh(t)
        assert t.receiving_status == "approved"
        assert t.stock_entered is False  # putaway still pending
        assert count == 0  # no stock entered


# ═══════════════════════════════════════════════════════════════════════════
# Rejection Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestRejection:
    def test_reject_items_no_rollback_needed(self, db_session, svc, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        t = _create_tracking(db_session, org_id, warehouse_id, session, item, "QR-REJ")

        slip = ReceivingSlip(
            id=uuid.uuid4(), organization_id=org_id, warehouse_id=warehouse_id,
            status="pending_review", session_id=session.id,
        )
        db_session.add(slip)
        db_session.flush()
        t.receiving_slip_id = slip.id
        db_session.flush()

        count = svc.reject_items(slip.id, reason="Damaged", rejected_by=uuid.uuid4())

        db_session.refresh(t)
        assert t.receiving_status == "rejected"
        assert t.rejection_reason == "Damaged"
        assert t.stock_entered is False
        assert count >= 1

    def test_reject_items_after_putaway_no_stock_loss(self, db_session, svc, org_id, warehouse_id):
        # Stock was never entered, so rejection is safe
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        bin_loc = _create_bin(db_session, org_id, warehouse_id)
        session = _create_session(db_session, org_id, warehouse_id)
        t = _create_tracking(db_session, org_id, warehouse_id, session, item, "QR-REJ2")

        slip = ReceivingSlip(
            id=uuid.uuid4(), organization_id=org_id, warehouse_id=warehouse_id,
            status="pending_review", session_id=session.id,
        )
        db_session.add(slip)
        db_session.flush()
        t.receiving_slip_id = slip.id
        t.putaway_status = "completed"
        t.bin_location_id = bin_loc.id
        db_session.flush()

        count = svc.reject_items(slip.id, reason="Wrong item", rejected_by=uuid.uuid4())

        db_session.refresh(t)
        assert t.receiving_status == "rejected"
        assert t.stock_entered is False  # Never entered
        assert count >= 1


# ═══════════════════════════════════════════════════════════════════════════
# Slip Summary Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestSlipSummary:
    def test_get_slip_summary(self, db_session, svc, org_id, warehouse_id):
        _create_warehouse(db_session, org_id, warehouse_id)
        item = _create_item(db_session, org_id)
        session = _create_session(db_session, org_id, warehouse_id)
        slip = ReceivingSlip(
            id=uuid.uuid4(), organization_id=org_id, warehouse_id=warehouse_id,
            status="pending_review", session_id=session.id,
        )
        db_session.add(slip)
        db_session.flush()

        # Scanned + pending
        t1 = _create_tracking(db_session, org_id, warehouse_id, session, item, "QR-A")
        t1.receiving_slip_id = slip.id
        # Scanned + completed
        t2 = _create_tracking(db_session, org_id, warehouse_id, session, item,
                              "QR-B", qr="QR-B")
        t2.receiving_slip_id = slip.id
        t2.putaway_status = "completed"
        db_session.flush()

        summary = svc.get_slip_summary(slip.id)
        assert len(summary) >= 1
        statuses = {(r["receiving_status"], r["putaway_status"]) for r in summary}
        assert ("scanned", "pending") in statuses
        assert ("scanned", "completed") in statuses
