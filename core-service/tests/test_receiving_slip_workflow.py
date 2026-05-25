"""Unit tests for receiving slip generation and review workflow.

Tests the InboundService methods:
- generate_receiving_slip: Creates slip from closed session
- approve_slip: Transitions PENDING_REVIEW → PENDING_PUTAWAY
- reject_slip: Transitions PENDING_REVIEW → REJECTED with reason
- flag_line_item: Flags items as SHORT or DAMAGED

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3, 7.4, 7.5
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.scan_session import ScanSession, ScanSessionItem
from app.services.inbound_service import InboundService


@pytest.fixture
def org_id():
    """Sample organization ID."""
    return uuid.uuid4()


@pytest.fixture
def worker_id():
    """Sample worker ID."""
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    """Sample warehouse ID."""
    return uuid.uuid4()


@pytest.fixture
def closed_session(db_session, org_id, worker_id, warehouse_id):
    """Create a closed scan session with items for testing."""
    session = ScanSession(
        id=uuid.uuid4(),
        organization_id=org_id,
        session_type="inbound",
        worker_id=worker_id,
        warehouse_id=warehouse_id,
        dock_location="Dock A",
        status="closed",
        total_boxes_scanned=4,
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
    )
    db_session.add(session)
    db_session.flush()

    # Add items: 2 boxes of SKU-A/BATCH-1, 1 box of SKU-A/BATCH-2, 1 box of SKU-B/BATCH-1
    items_data = [
        ("qr-001", "SKU-A", 10, "BATCH-1"),
        ("qr-002", "SKU-A", 15, "BATCH-1"),
        ("qr-003", "SKU-A", 20, "BATCH-2"),
        ("qr-004", "SKU-B", 5, "BATCH-1"),
    ]
    for qr_id, sku, qty, batch in items_data:
        item = ScanSessionItem(
            id=uuid.uuid4(),
            organization_id=org_id,
            session_id=session.id,
            qr_identifier=qr_id,
            sku=sku,
            raw_quantity=qty,
            batch_number=batch,
            raw_qr_data=f'{{"id":"{qr_id}","sku":"{sku}","qty":{qty},"batch":"{batch}"}}',
        )
        db_session.add(item)

    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture
def open_session(db_session, org_id, worker_id, warehouse_id):
    """Create an open scan session for testing."""
    session = ScanSession(
        id=uuid.uuid4(),
        organization_id=org_id,
        session_type="inbound",
        worker_id=worker_id,
        warehouse_id=warehouse_id,
        status="open",
        total_boxes_scanned=0,
        started_at=datetime.now(UTC),
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture
def inbound_service(db_session):
    """Create an InboundService instance."""
    return InboundService(db_session)


@pytest.fixture
def pending_review_slip(inbound_service, closed_session, org_id):
    """Create a receiving slip in PENDING_REVIEW status."""
    result = inbound_service.generate_receiving_slip(closed_session.id, org_id)
    return result


class TestGenerateReceivingSlip:
    """Tests for generate_receiving_slip method."""

    def test_generates_slip_from_closed_session(
        self, inbound_service, closed_session, org_id
    ):
        """A closed session with items should produce a receiving slip."""
        result = inbound_service.generate_receiving_slip(closed_session.id, org_id)

        assert result["status"] == "pending_review"
        assert result["session_id"] == str(closed_session.id)
        assert result["warehouse_id"] == str(closed_session.warehouse_id)
        assert result["slip_number"] is not None
        assert result["slip_number"] != ""

    def test_groups_items_by_sku_and_batch(
        self, inbound_service, closed_session, org_id
    ):
        """Items should be grouped by SKU+batch with aggregated quantities."""
        result = inbound_service.generate_receiving_slip(closed_session.id, org_id)

        items = result["items"]
        # Should have 3 groups: SKU-A/BATCH-1, SKU-A/BATCH-2, SKU-B/BATCH-1
        assert len(items) == 3

        # Find SKU-A/BATCH-1 group (2 boxes, qty 10+15=25)
        sku_a_batch_1 = next(
            (
                i
                for i in items
                if i["sku"] == "SKU-A" and i["batch_number"] == "BATCH-1"
            ),
            None,
        )
        assert sku_a_batch_1 is not None
        assert sku_a_batch_1["quantity"] == 25
        assert sku_a_batch_1["box_count"] == 2

        # Find SKU-A/BATCH-2 group (1 box, qty 20)
        sku_a_batch_2 = next(
            (
                i
                for i in items
                if i["sku"] == "SKU-A" and i["batch_number"] == "BATCH-2"
            ),
            None,
        )
        assert sku_a_batch_2 is not None
        assert sku_a_batch_2["quantity"] == 20
        assert sku_a_batch_2["box_count"] == 1

        # Find SKU-B/BATCH-1 group (1 box, qty 5)
        sku_b_batch_1 = next(
            (
                i
                for i in items
                if i["sku"] == "SKU-B" and i["batch_number"] == "BATCH-1"
            ),
            None,
        )
        assert sku_b_batch_1 is not None
        assert sku_b_batch_1["quantity"] == 5
        assert sku_b_batch_1["box_count"] == 1

    def test_computes_totals_correctly(self, inbound_service, closed_session, org_id):
        """Total boxes and total items should be computed correctly."""
        result = inbound_service.generate_receiving_slip(closed_session.id, org_id)

        assert result["total_boxes"] == 4  # 4 scan items
        assert result["total_items"] == 50  # 10+15+20+5

    def test_generates_unique_slip_number(
        self, inbound_service, closed_session, org_id
    ):
        """Slip number should be generated using document numbering service."""
        result = inbound_service.generate_receiving_slip(closed_session.id, org_id)

        assert result["slip_number"] is not None
        # Should follow RS-YYYY-NNNNN format
        assert "RS" in result["slip_number"]

    def test_raises_not_found_for_missing_session(self, inbound_service, org_id):
        """Should raise NotFoundError for non-existent session."""
        fake_id = uuid.uuid4()

        with pytest.raises(NotFoundError) as exc_info:
            inbound_service.generate_receiving_slip(fake_id, org_id)

        assert "Scan session not found" in exc_info.value.message

    def test_raises_state_error_for_open_session(
        self, inbound_service, open_session, org_id
    ):
        """Should raise StateError if session is not closed."""
        with pytest.raises(StateError) as exc_info:
            inbound_service.generate_receiving_slip(open_session.id, org_id)

        assert "not closed" in exc_info.value.message
        assert exc_info.value.current_state == "open"

    def test_raises_validation_error_for_empty_session(
        self, db_session, inbound_service, org_id, worker_id, warehouse_id
    ):
        """Should raise ValidationError if session has no items."""
        # Create a closed session with no items
        empty_session = ScanSession(
            id=uuid.uuid4(),
            organization_id=org_id,
            session_type="inbound",
            worker_id=worker_id,
            warehouse_id=warehouse_id,
            status="closed",
            total_boxes_scanned=0,
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
        )
        db_session.add(empty_session)
        db_session.commit()

        with pytest.raises(ValidationError) as exc_info:
            inbound_service.generate_receiving_slip(empty_session.id, org_id)

        assert "empty session" in exc_info.value.message

    def test_all_items_have_ok_flag(self, inbound_service, closed_session, org_id):
        """All generated line items should have flag='ok' by default."""
        result = inbound_service.generate_receiving_slip(closed_session.id, org_id)

        for item in result["items"]:
            assert item["flag"] == "ok"


class TestApproveSlip:
    """Tests for approve_slip method."""

    def test_approves_pending_review_slip(
        self, inbound_service, pending_review_slip, org_id
    ):
        """Should transition slip from PENDING_REVIEW to PENDING_PUTAWAY."""
        slip_id = uuid.UUID(pending_review_slip["id"])

        result = inbound_service.approve_slip(slip_id, org_id)

        assert result["status"] == "pending_putaway"
        assert result["id"] == pending_review_slip["id"]

    def test_raises_not_found_for_missing_slip(self, inbound_service, org_id):
        """Should raise NotFoundError for non-existent slip."""
        fake_id = uuid.uuid4()

        with pytest.raises(NotFoundError) as exc_info:
            inbound_service.approve_slip(fake_id, org_id)

        assert "Receiving slip not found" in exc_info.value.message

    def test_raises_state_error_for_non_pending_review_slip(
        self, inbound_service, pending_review_slip, org_id
    ):
        """Should raise StateError if slip is not in PENDING_REVIEW status."""
        slip_id = uuid.UUID(pending_review_slip["id"])

        # Approve it first
        inbound_service.approve_slip(slip_id, org_id)

        # Try to approve again (now in pending_putaway)
        with pytest.raises(StateError) as exc_info:
            inbound_service.approve_slip(slip_id, org_id)

        assert exc_info.value.current_state == "pending_putaway"
        assert "pending_review" in exc_info.value.required_state


class TestRejectSlip:
    """Tests for reject_slip method."""

    def test_rejects_pending_review_slip_with_reason(
        self, inbound_service, pending_review_slip, org_id
    ):
        """Should transition slip to REJECTED with reason recorded."""
        slip_id = uuid.UUID(pending_review_slip["id"])
        reason = "Items do not match purchase order"

        result = inbound_service.reject_slip(slip_id, reason, org_id)

        assert result["status"] == "rejected"
        assert result["rejection_reason"] == reason

    def test_raises_not_found_for_missing_slip(self, inbound_service, org_id):
        """Should raise NotFoundError for non-existent slip."""
        fake_id = uuid.uuid4()

        with pytest.raises(NotFoundError) as exc_info:
            inbound_service.reject_slip(fake_id, "some reason", org_id)

        assert "Receiving slip not found" in exc_info.value.message

    def test_raises_state_error_for_non_pending_review_slip(
        self, inbound_service, pending_review_slip, org_id
    ):
        """Should raise StateError if slip is not in PENDING_REVIEW status."""
        slip_id = uuid.UUID(pending_review_slip["id"])

        # Reject it first
        inbound_service.reject_slip(slip_id, "first rejection", org_id)

        # Try to reject again (now in rejected)
        with pytest.raises(StateError) as exc_info:
            inbound_service.reject_slip(slip_id, "second rejection", org_id)

        assert exc_info.value.current_state == "rejected"

    def test_raises_validation_error_for_empty_reason(
        self, inbound_service, pending_review_slip, org_id
    ):
        """Should raise ValidationError if reason is empty."""
        slip_id = uuid.UUID(pending_review_slip["id"])

        with pytest.raises(ValidationError) as exc_info:
            inbound_service.reject_slip(slip_id, "", org_id)

        assert "Rejection reason is required" in exc_info.value.message

    def test_raises_validation_error_for_whitespace_reason(
        self, inbound_service, pending_review_slip, org_id
    ):
        """Should raise ValidationError if reason is only whitespace."""
        slip_id = uuid.UUID(pending_review_slip["id"])

        with pytest.raises(ValidationError) as exc_info:
            inbound_service.reject_slip(slip_id, "   ", org_id)

        assert "Rejection reason is required" in exc_info.value.message


class TestFlagLineItem:
    """Tests for flag_line_item method."""

    def test_flags_item_as_short(self, inbound_service, pending_review_slip, org_id):
        """Should update item flag to 'short'."""
        slip_id = uuid.UUID(pending_review_slip["id"])
        item_id = uuid.UUID(pending_review_slip["items"][0]["id"])

        result = inbound_service.flag_line_item(
            slip_id, item_id, "short", "Missing 5 units", org_id
        )

        assert result["flag"] == "short"
        assert result["notes"] == "Missing 5 units"

    def test_flags_item_as_damaged(self, inbound_service, pending_review_slip, org_id):
        """Should update item flag to 'damaged'."""
        slip_id = uuid.UUID(pending_review_slip["id"])
        item_id = uuid.UUID(pending_review_slip["items"][0]["id"])

        result = inbound_service.flag_line_item(
            slip_id, item_id, "damaged", "Water damage on boxes", org_id
        )

        assert result["flag"] == "damaged"
        assert result["notes"] == "Water damage on boxes"

    def test_flags_item_with_no_notes(
        self, inbound_service, pending_review_slip, org_id
    ):
        """Should allow flagging without notes."""
        slip_id = uuid.UUID(pending_review_slip["id"])
        item_id = uuid.UUID(pending_review_slip["items"][0]["id"])

        result = inbound_service.flag_line_item(slip_id, item_id, "short", None, org_id)

        assert result["flag"] == "short"

    def test_raises_validation_error_for_invalid_flag(
        self, inbound_service, pending_review_slip, org_id
    ):
        """Should raise ValidationError for invalid flag values."""
        slip_id = uuid.UUID(pending_review_slip["id"])
        item_id = uuid.UUID(pending_review_slip["items"][0]["id"])

        with pytest.raises(ValidationError) as exc_info:
            inbound_service.flag_line_item(
                slip_id, item_id, "invalid_flag", None, org_id
            )

        assert "Invalid flag value" in exc_info.value.message

    def test_raises_not_found_for_missing_slip(self, inbound_service, org_id):
        """Should raise NotFoundError for non-existent slip."""
        fake_slip_id = uuid.uuid4()
        fake_item_id = uuid.uuid4()

        with pytest.raises(NotFoundError) as exc_info:
            inbound_service.flag_line_item(
                fake_slip_id, fake_item_id, "short", None, org_id
            )

        assert "Receiving slip not found" in exc_info.value.message

    def test_raises_not_found_for_missing_item(
        self, inbound_service, pending_review_slip, org_id
    ):
        """Should raise NotFoundError for non-existent item."""
        slip_id = uuid.UUID(pending_review_slip["id"])
        fake_item_id = uuid.uuid4()

        with pytest.raises(NotFoundError) as exc_info:
            inbound_service.flag_line_item(slip_id, fake_item_id, "short", None, org_id)

        assert "Receiving slip item not found" in exc_info.value.message

    def test_raises_state_error_for_non_pending_review_slip(
        self, inbound_service, pending_review_slip, org_id
    ):
        """Should raise StateError if slip is not in PENDING_REVIEW status."""
        slip_id = uuid.UUID(pending_review_slip["id"])
        item_id = uuid.UUID(pending_review_slip["items"][0]["id"])

        # Approve the slip first
        inbound_service.approve_slip(slip_id, org_id)

        # Try to flag an item (slip is now pending_putaway)
        with pytest.raises(StateError) as exc_info:
            inbound_service.flag_line_item(slip_id, item_id, "short", None, org_id)

        assert exc_info.value.current_state == "pending_putaway"

    def test_raises_validation_error_for_item_not_belonging_to_slip(
        self,
        db_session,
        inbound_service,
        pending_review_slip,
        org_id,
        worker_id,
        warehouse_id,
    ):
        """Should raise ValidationError if item doesn't belong to the slip."""
        slip_id = uuid.UUID(pending_review_slip["id"])

        # Create another session and slip to get an item from a different slip
        other_session = ScanSession(
            id=uuid.uuid4(),
            organization_id=org_id,
            session_type="inbound",
            worker_id=worker_id,
            warehouse_id=warehouse_id,
            status="closed",
            total_boxes_scanned=1,
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
        )
        db_session.add(other_session)
        db_session.flush()

        other_item = ScanSessionItem(
            id=uuid.uuid4(),
            organization_id=org_id,
            session_id=other_session.id,
            qr_identifier="qr-other-001",
            sku="OTHER-SKU",
            raw_quantity=10,
            batch_number="OTHER-BATCH",
            raw_qr_data='{"id":"qr-other-001","sku":"OTHER-SKU","qty":10,"batch":"OTHER-BATCH"}',
        )
        db_session.add(other_item)
        db_session.commit()

        # Generate a slip from the other session
        other_slip = inbound_service.generate_receiving_slip(other_session.id, org_id)
        other_item_id = uuid.UUID(other_slip["items"][0]["id"])

        # Try to flag the other slip's item on the first slip
        with pytest.raises(ValidationError) as exc_info:
            inbound_service.flag_line_item(
                slip_id, other_item_id, "short", None, org_id
            )

        assert "does not belong" in exc_info.value.message
