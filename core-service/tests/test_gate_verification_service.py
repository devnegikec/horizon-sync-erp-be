"""Unit tests for GateVerificationService."""

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.base import PickListStatus
from app.models.item import Item
from app.models.pick_list import PickList, PickListItem
from app.services.gate_verification_service import GateVerificationService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def worker_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id(db_session, org_id):
    """Create a warehouse record."""
    from app.models.warehouse import Warehouse

    wh = Warehouse(
        id=uuid.uuid4(),
        organization_id=org_id,
        code="WH-GATE",
        name="Gate Test Warehouse",
    )
    db_session.add(wh)
    db_session.commit()
    db_session.refresh(wh)
    return wh.id


@pytest.fixture
def test_item(db_session, org_id):
    """Create a test item."""
    item = Item(
        id=uuid.uuid4(),
        organization_id=org_id,
        item_code="ITEM-001",
        item_name="Test Widget",
        item_type="stock",
        uom="Nos",
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture
def completed_pick_list(db_session, org_id, warehouse_id, test_item):
    """Create a completed pick list with items."""
    pl = PickList(
        id=uuid.uuid4(),
        organization_id=org_id,
        pick_list_no="PL-TEST-001",
        warehouse_id=warehouse_id,
        status=PickListStatus.COMPLETED,
        completed_at=datetime.now(UTC),
    )
    db_session.add(pl)
    db_session.flush()

    pl_item = PickListItem(
        id=uuid.uuid4(),
        organization_id=org_id,
        pick_list_id=pl.id,
        item_id=test_item.id,
        warehouse_id=warehouse_id,
        qty=Decimal("100"),
        picked_qty=Decimal("100"),
        uom="Nos",
    )
    db_session.add(pl_item)
    db_session.commit()
    db_session.refresh(pl)
    return pl


@pytest.fixture
def draft_pick_list(db_session, org_id, warehouse_id, test_item):
    """Create a draft pick list (not completed)."""
    pl = PickList(
        id=uuid.uuid4(),
        organization_id=org_id,
        pick_list_no="PL-TEST-002",
        warehouse_id=warehouse_id,
        status=PickListStatus.DRAFT,
    )
    db_session.add(pl)
    db_session.commit()
    db_session.refresh(pl)
    return pl


@pytest.fixture
def gate_service(db_session):
    return GateVerificationService(db_session)


def _make_qr_payload(
    qr_id: str = "QR-GATE-001",
    sku: str = "ITEM-001",
    qty: int = 50,
    batch: str = "BATCH-2025-01",
) -> str:
    """Helper to create a valid QR payload JSON string."""
    return json.dumps({"id": qr_id, "sku": sku, "qty": qty, "batch": batch})


class TestStartSession:
    """Tests for start_session method."""

    def test_creates_open_session_with_completed_pick_list(
        self, gate_service, org_id, worker_id, completed_pick_list
    ):
        """Should create a gate session linked to a completed pick list."""
        result = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
            vehicle_number="KA-01-AB-1234",
            driver_name="John Driver",
            driver_contact="9876543210",
        )

        assert result["status"] == "open"
        assert result["pick_list_id"] == str(completed_pick_list.id)
        assert result["worker_id"] == str(worker_id)
        assert result["vehicle_number"] == "KA-01-AB-1234"
        assert result["driver_name"] == "John Driver"
        assert result["driver_contact"] == "9876543210"
        assert result["verified_at"] is None
        assert result["items"] == []

    def test_raises_not_found_for_missing_pick_list(
        self, gate_service, org_id, worker_id
    ):
        """Should raise NotFoundError if pick list doesn't exist."""
        with pytest.raises(NotFoundError) as exc_info:
            gate_service.start_session(
                pick_list_id=uuid.uuid4(),
                worker_id=worker_id,
                org_id=org_id,
            )
        assert "Pick list not found" in str(exc_info.value)

    def test_raises_state_error_for_non_completed_pick_list(
        self, gate_service, org_id, worker_id, draft_pick_list
    ):
        """Should raise StateError if pick list is not completed."""
        with pytest.raises(StateError) as exc_info:
            gate_service.start_session(
                pick_list_id=draft_pick_list.id,
                worker_id=worker_id,
                org_id=org_id,
            )
        assert "completed" in str(exc_info.value)


class TestRecordGateScan:
    """Tests for record_gate_scan method."""

    def test_records_verified_scan_for_valid_item(
        self, gate_service, org_id, worker_id, completed_pick_list, test_item
    ):
        """Should mark scan as VERIFIED when item is on the pick list."""
        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
        )

        result = gate_service.record_gate_scan(
            session_id=uuid.UUID(session["id"]),
            qr_payload=_make_qr_payload(sku=test_item.item_code),
            worker_id=worker_id,
            org_id=org_id,
        )

        assert result["status"] == "verified"
        assert result["sku"] == test_item.item_code
        assert result["quantity"] == 50

    def test_records_unauthorized_scan_for_unknown_item(
        self, gate_service, org_id, worker_id, completed_pick_list
    ):
        """Should mark scan as UNAUTHORIZED when item is not on the pick list."""
        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
        )

        result = gate_service.record_gate_scan(
            session_id=uuid.UUID(session["id"]),
            qr_payload=_make_qr_payload(sku="UNKNOWN-SKU"),
            worker_id=worker_id,
            org_id=org_id,
        )

        assert result["status"] == "unauthorized"
        assert result["sku"] == "UNKNOWN-SKU"

    def test_rejects_duplicate_scan(
        self, gate_service, org_id, worker_id, completed_pick_list, test_item
    ):
        """Should reject duplicate QR identifier within the same session."""
        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
        )
        session_id = uuid.UUID(session["id"])

        # First scan succeeds
        gate_service.record_gate_scan(
            session_id=session_id,
            qr_payload=_make_qr_payload(qr_id="QR-DUP-001"),
            worker_id=worker_id,
            org_id=org_id,
        )

        # Second scan with same QR ID should fail
        with pytest.raises(ValidationError) as exc_info:
            gate_service.record_gate_scan(
                session_id=session_id,
                qr_payload=_make_qr_payload(qr_id="QR-DUP-001"),
                worker_id=worker_id,
                org_id=org_id,
            )
        assert "Duplicate scan" in str(exc_info.value)

    def test_raises_not_found_for_missing_session(
        self, gate_service, org_id, worker_id
    ):
        """Should raise NotFoundError if session doesn't exist."""
        with pytest.raises(NotFoundError):
            gate_service.record_gate_scan(
                session_id=uuid.uuid4(),
                qr_payload=_make_qr_payload(),
                worker_id=worker_id,
                org_id=org_id,
            )

    def test_raises_state_error_for_non_open_session(
        self, gate_service, db_session, org_id, worker_id, completed_pick_list
    ):
        """Should raise StateError if session is not open."""
        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
        )

        # Manually close the session to simulate verified state
        from app.models.gate_verification import GateVerificationSession

        gate_session = (
            db_session.query(GateVerificationSession)
            .filter(GateVerificationSession.id == uuid.UUID(session["id"]))
            .first()
        )
        gate_session.status = "verified"
        db_session.commit()

        with pytest.raises(StateError):
            gate_service.record_gate_scan(
                session_id=uuid.UUID(session["id"]),
                qr_payload=_make_qr_payload(),
                worker_id=worker_id,
                org_id=org_id,
            )


class TestGetSessionProgress:
    """Tests for get_session_progress method."""

    def test_returns_progress_with_no_scans(
        self, gate_service, org_id, worker_id, completed_pick_list
    ):
        """Should return zero progress when no scans have been made."""
        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
        )

        progress = gate_service.get_session_progress(
            session_id=uuid.UUID(session["id"]),
            org_id=org_id,
        )

        assert progress["total_scanned"] == 0
        assert progress["verified_count"] == 0
        assert progress["unauthorized_count"] == 0
        assert progress["verified_qty"] == 0
        assert progress["expected_total_qty"] == 100  # from pick list item
        assert progress["all_verified"] is False

    def test_returns_progress_after_scans(
        self, gate_service, org_id, worker_id, completed_pick_list, test_item
    ):
        """Should return correct progress after scanning items."""
        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
        )
        session_id = uuid.UUID(session["id"])

        # Scan a verified item
        gate_service.record_gate_scan(
            session_id=session_id,
            qr_payload=_make_qr_payload(qr_id="QR-P1", sku=test_item.item_code, qty=50),
            worker_id=worker_id,
            org_id=org_id,
        )

        # Scan an unauthorized item
        gate_service.record_gate_scan(
            session_id=session_id,
            qr_payload=_make_qr_payload(qr_id="QR-P2", sku="BAD-SKU", qty=10),
            worker_id=worker_id,
            org_id=org_id,
        )

        progress = gate_service.get_session_progress(
            session_id=session_id,
            org_id=org_id,
        )

        assert progress["total_scanned"] == 2
        assert progress["verified_count"] == 1
        assert progress["unauthorized_count"] == 1
        assert progress["verified_qty"] == 50
        assert progress["all_verified"] is False

    def test_raises_not_found_for_missing_session(self, gate_service, org_id):
        """Should raise NotFoundError if session doesn't exist."""
        with pytest.raises(NotFoundError):
            gate_service.get_session_progress(
                session_id=uuid.uuid4(),
                org_id=org_id,
            )


class TestVerifySession:
    """Tests for verify_session method."""

    def test_verifies_session_when_all_items_scanned(
        self, gate_service, org_id, worker_id, completed_pick_list, test_item
    ):
        """Should transition to VERIFIED when all items are scanned."""
        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
        )
        session_id = uuid.UUID(session["id"])

        # Scan enough items to cover the pick list qty (100)
        gate_service.record_gate_scan(
            session_id=session_id,
            qr_payload=_make_qr_payload(qr_id="QR-V1", sku=test_item.item_code, qty=60),
            worker_id=worker_id,
            org_id=org_id,
        )
        gate_service.record_gate_scan(
            session_id=session_id,
            qr_payload=_make_qr_payload(qr_id="QR-V2", sku=test_item.item_code, qty=40),
            worker_id=worker_id,
            org_id=org_id,
        )

        result = gate_service.verify_session(
            session_id=session_id,
            org_id=org_id,
        )

        assert result["status"] == "verified"
        assert result["verified_at"] is not None

    def test_raises_validation_error_when_not_all_items_scanned(
        self, gate_service, org_id, worker_id, completed_pick_list, test_item
    ):
        """Should raise ValidationError if verified qty is less than expected."""
        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
        )
        session_id = uuid.UUID(session["id"])

        # Only scan 50 of 100 expected
        gate_service.record_gate_scan(
            session_id=session_id,
            qr_payload=_make_qr_payload(qr_id="QR-V1", sku=test_item.item_code, qty=50),
            worker_id=worker_id,
            org_id=org_id,
        )

        with pytest.raises(ValidationError) as exc_info:
            gate_service.verify_session(
                session_id=session_id,
                org_id=org_id,
            )
        assert "verified quantity" in str(exc_info.value).lower()

    def test_raises_validation_error_when_unauthorized_items_present(
        self, gate_service, org_id, worker_id, completed_pick_list, test_item
    ):
        """Should raise ValidationError if unauthorized items are present."""
        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
        )
        session_id = uuid.UUID(session["id"])

        # Scan enough verified items
        gate_service.record_gate_scan(
            session_id=session_id,
            qr_payload=_make_qr_payload(
                qr_id="QR-V1", sku=test_item.item_code, qty=100
            ),
            worker_id=worker_id,
            org_id=org_id,
        )
        # Also scan an unauthorized item
        gate_service.record_gate_scan(
            session_id=session_id,
            qr_payload=_make_qr_payload(qr_id="QR-BAD", sku="UNKNOWN", qty=5),
            worker_id=worker_id,
            org_id=org_id,
        )

        with pytest.raises(ValidationError) as exc_info:
            gate_service.verify_session(
                session_id=session_id,
                org_id=org_id,
            )
        assert "unauthorized" in str(exc_info.value).lower()

    def test_raises_state_error_for_already_verified_session(
        self,
        gate_service,
        db_session,
        org_id,
        worker_id,
        completed_pick_list,
        test_item,
    ):
        """Should raise StateError if session is already verified."""
        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
        )
        session_id = uuid.UUID(session["id"])

        # Scan all items and verify
        gate_service.record_gate_scan(
            session_id=session_id,
            qr_payload=_make_qr_payload(
                qr_id="QR-V1", sku=test_item.item_code, qty=100
            ),
            worker_id=worker_id,
            org_id=org_id,
        )
        gate_service.verify_session(session_id=session_id, org_id=org_id)

        # Try to verify again
        with pytest.raises(StateError):
            gate_service.verify_session(session_id=session_id, org_id=org_id)

    def test_raises_not_found_for_missing_session(self, gate_service, org_id):
        """Should raise NotFoundError if session doesn't exist."""
        with pytest.raises(NotFoundError):
            gate_service.verify_session(
                session_id=uuid.uuid4(),
                org_id=org_id,
            )


class TestVerifySessionDispatchIntegration:
    """Tests for verify_session dispatch creation integration.

    Validates that when a gate session is verified, a dispatch record is
    created atomically with stock deduction and dispatch number generation.

    Requirements: 12.6, 13.1, 13.4, 13.5
    """

    def test_verify_creates_dispatch_record(
        self,
        gate_service,
        db_session,
        org_id,
        worker_id,
        completed_pick_list,
        test_item,
    ):
        """Should create a dispatch record when session is verified.

        Requirements: 12.6, 13.1
        """
        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
            vehicle_number="KA-01-AB-1234",
            driver_name="John Driver",
        )
        session_id = uuid.UUID(session["id"])

        # Scan all items
        gate_service.record_gate_scan(
            session_id=session_id,
            qr_payload=_make_qr_payload(
                qr_id="QR-D1", sku=test_item.item_code, qty=100
            ),
            worker_id=worker_id,
            org_id=org_id,
        )

        result = gate_service.verify_session(session_id=session_id, org_id=org_id)

        # Verify dispatch record is included in the response
        assert "dispatch" in result
        dispatch = result["dispatch"]
        assert dispatch["pick_list_id"] == str(completed_pick_list.id)
        assert dispatch["gate_session_id"] == str(session_id)
        assert dispatch["vehicle_number"] == "KA-01-AB-1234"
        assert dispatch["driver_name"] == "John Driver"
        assert dispatch["dispatched_at"] is not None

    def test_verify_generates_unique_dispatch_number(
        self,
        gate_service,
        db_session,
        org_id,
        worker_id,
        completed_pick_list,
        test_item,
    ):
        """Should generate a unique dispatch number via document numbering service.

        Requirements: 13.5
        """
        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
        )
        session_id = uuid.UUID(session["id"])

        gate_service.record_gate_scan(
            session_id=session_id,
            qr_payload=_make_qr_payload(
                qr_id="QR-DN1", sku=test_item.item_code, qty=100
            ),
            worker_id=worker_id,
            org_id=org_id,
        )

        result = gate_service.verify_session(session_id=session_id, org_id=org_id)

        dispatch = result["dispatch"]
        # Dispatch number should follow the pattern DSP-YYYY-NNNNN
        assert dispatch["dispatch_number"] is not None
        assert "DSP" in dispatch["dispatch_number"]

    def test_verify_decrements_stock_levels(
        self,
        gate_service,
        db_session,
        org_id,
        worker_id,
        completed_pick_list,
        test_item,
        warehouse_id,
    ):
        """Should decrement warehouse stock levels for dispatched items.

        Requirements: 13.4
        """
        from app.models.stock_level import StockLevel

        # Create a stock level record for the item/warehouse
        stock_level = StockLevel(
            id=uuid.uuid4(),
            organization_id=org_id,
            product_id=test_item.id,
            warehouse_id=warehouse_id,
            quantity_on_hand=500,
            quantity_reserved=0,
            quantity_available=500,
        )
        db_session.add(stock_level)
        db_session.commit()

        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
        )
        session_id = uuid.UUID(session["id"])

        gate_service.record_gate_scan(
            session_id=session_id,
            qr_payload=_make_qr_payload(
                qr_id="QR-STK1", sku=test_item.item_code, qty=100
            ),
            worker_id=worker_id,
            org_id=org_id,
        )

        gate_service.verify_session(session_id=session_id, org_id=org_id)

        # Refresh stock level and verify decrement
        db_session.refresh(stock_level)
        # Pick list item has qty=100 and picked_qty=100
        assert stock_level.quantity_on_hand == 400

    def test_verify_links_dispatch_to_pick_list(
        self,
        gate_service,
        db_session,
        org_id,
        worker_id,
        completed_pick_list,
        test_item,
    ):
        """Should update pick list with dispatch record reference.

        Requirements: 13.2
        """
        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
        )
        session_id = uuid.UUID(session["id"])

        gate_service.record_gate_scan(
            session_id=session_id,
            qr_payload=_make_qr_payload(
                qr_id="QR-LNK1", sku=test_item.item_code, qty=100
            ),
            worker_id=worker_id,
            org_id=org_id,
        )

        result = gate_service.verify_session(session_id=session_id, org_id=org_id)

        # Refresh pick list and verify dispatch_record_id is set
        db_session.refresh(completed_pick_list)
        dispatch_id = uuid.UUID(result["dispatch"]["id"])
        assert completed_pick_list.dispatch_record_id == dispatch_id

    def test_verify_and_dispatch_are_atomic(
        self,
        gate_service,
        db_session,
        org_id,
        worker_id,
        completed_pick_list,
        test_item,
    ):
        """Session verification and dispatch creation should happen in same transaction.

        If verify_session succeeds, both the session status change and the
        dispatch record should be persisted together.
        """
        from app.models.dispatch_record import DispatchRecord

        session = gate_service.start_session(
            pick_list_id=completed_pick_list.id,
            worker_id=worker_id,
            org_id=org_id,
        )
        session_id = uuid.UUID(session["id"])

        gate_service.record_gate_scan(
            session_id=session_id,
            qr_payload=_make_qr_payload(
                qr_id="QR-ATM1", sku=test_item.item_code, qty=100
            ),
            worker_id=worker_id,
            org_id=org_id,
        )

        result = gate_service.verify_session(session_id=session_id, org_id=org_id)

        # Both session and dispatch should be persisted
        assert result["status"] == "verified"
        assert result["dispatch"] is not None

        # Verify dispatch record exists in the database
        dispatch_record = (
            db_session.query(DispatchRecord)
            .filter(DispatchRecord.gate_session_id == session_id)
            .first()
        )
        assert dispatch_record is not None
        assert dispatch_record.pick_list_id == completed_pick_list.id
