"""Unit tests for InboundService scan session management."""

import json
import uuid

import pytest

from app.services.inbound_service import InboundService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def worker_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id(db_session, org_id):
    """Create a warehouse record for FK constraints (SQLite ignores FKs but good practice)."""
    from app.models.warehouse import Warehouse

    wh = Warehouse(
        id=uuid.uuid4(),
        organization_id=org_id,
        code="WH-TEST",
        name="Test Warehouse",
    )
    db_session.add(wh)
    db_session.commit()
    db_session.refresh(wh)
    return wh.id


@pytest.fixture
def inbound_service(db_session):
    return InboundService(db_session)


def _make_qr_payload(
    qr_id: str = "QR-001",
    sku: str = "ITEM-001",
    qty: int = 50,
    batch: str = "BATCH-2025-01",
) -> str:
    """Helper to create a valid QR payload JSON string."""
    return json.dumps({"id": qr_id, "sku": sku, "qty": qty, "batch": batch})


class TestStartSession:
    """Tests for start_session method."""

    def test_creates_open_session(
        self, inbound_service, org_id, worker_id, warehouse_id
    ):
        """Should create a session with status 'open'."""
        result = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
            dock_location="Dock A",
        )

        assert result["status"] == "open"
        assert result["session_type"] == "inbound"
        assert result["worker_id"] == str(worker_id)
        assert result["warehouse_id"] == str(warehouse_id)
        assert result["dock_location"] == "Dock A"
        assert result["total_boxes_scanned"] == 0
        assert result["started_at"] is not None

    def test_creates_session_without_dock_location(
        self, inbound_service, org_id, worker_id, warehouse_id
    ):
        """Should create a session even without dock_location."""
        result = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )

        assert result["status"] == "open"
        assert result["dock_location"] is None


class TestRecordScan:
    """Tests for record_scan method."""

    def test_records_valid_scan(self, inbound_service, org_id, worker_id, warehouse_id):
        """Should successfully record a valid QR scan."""
        session = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session["id"])

        qr_data = _make_qr_payload()
        result = inbound_service.record_scan(
            session_id=session_id,
            qr_data=qr_data,
            worker_id=worker_id,
            organization_id=org_id,
        )

        assert result["sku"] == "ITEM-001"
        assert result["raw_quantity"] == 50
        assert result["batch_number"] == "BATCH-2025-01"
        assert result["qr_identifier"] == "QR-001"
        assert result["total_boxes_scanned"] == 1

    def test_rejects_duplicate_scan(
        self, inbound_service, org_id, worker_id, warehouse_id
    ):
        """Should reject a duplicate QR identifier within the same session."""
        from app.core.exceptions import ValidationError

        session = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session["id"])

        qr_data = _make_qr_payload(qr_id="QR-DUP")
        inbound_service.record_scan(
            session_id=session_id,
            qr_data=qr_data,
            worker_id=worker_id,
            organization_id=org_id,
        )

        # Second scan with same QR identifier should fail
        with pytest.raises(ValidationError, match="Duplicate scan"):
            inbound_service.record_scan(
                session_id=session_id,
                qr_data=qr_data,
                worker_id=worker_id,
                organization_id=org_id,
            )

    def test_rejects_scan_on_closed_session(
        self, inbound_service, org_id, worker_id, warehouse_id
    ):
        """Should reject scans on a closed session."""
        from app.core.exceptions import StateError

        session = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session["id"])

        # Close the session
        inbound_service.end_session(
            session_id=session_id,
            worker_id=worker_id,
            organization_id=org_id,
        )

        # Try to scan on closed session
        qr_data = _make_qr_payload()
        with pytest.raises(StateError, match="Cannot record scan on a closed session"):
            inbound_service.record_scan(
                session_id=session_id,
                qr_data=qr_data,
                worker_id=worker_id,
                organization_id=org_id,
            )

    def test_rejects_invalid_qr_payload(
        self, inbound_service, org_id, worker_id, warehouse_id
    ):
        """Should reject invalid QR payload."""
        from app.core.exceptions import ValidationError

        session = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session["id"])

        with pytest.raises(ValidationError, match="Invalid QR payload"):
            inbound_service.record_scan(
                session_id=session_id,
                qr_data="not-valid-json",
                worker_id=worker_id,
                organization_id=org_id,
            )

    def test_rejects_scan_on_nonexistent_session(
        self, inbound_service, org_id, worker_id
    ):
        """Should raise NotFoundError for non-existent session."""
        from app.core.exceptions import NotFoundError

        qr_data = _make_qr_payload()
        with pytest.raises(NotFoundError, match="Scan session not found"):
            inbound_service.record_scan(
                session_id=uuid.uuid4(),
                qr_data=qr_data,
                worker_id=worker_id,
                organization_id=org_id,
            )

    def test_increments_box_count(
        self, inbound_service, org_id, worker_id, warehouse_id
    ):
        """Should increment total_boxes_scanned with each scan."""
        session = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session["id"])

        for i in range(3):
            result = inbound_service.record_scan(
                session_id=session_id,
                qr_data=_make_qr_payload(qr_id=f"QR-{i:03d}"),
                worker_id=worker_id,
                organization_id=org_id,
            )

        assert result["total_boxes_scanned"] == 3


class TestEndSession:
    """Tests for end_session method."""

    def test_closes_session_and_generates_slip(
        self, inbound_service, org_id, worker_id, warehouse_id
    ):
        """Should close session and generate a receiving slip."""
        session = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session["id"])

        # Record some scans
        inbound_service.record_scan(
            session_id=session_id,
            qr_data=_make_qr_payload(qr_id="QR-001", sku="ITEM-A", qty=10, batch="B1"),
            worker_id=worker_id,
            organization_id=org_id,
        )
        inbound_service.record_scan(
            session_id=session_id,
            qr_data=_make_qr_payload(qr_id="QR-002", sku="ITEM-A", qty=20, batch="B1"),
            worker_id=worker_id,
            organization_id=org_id,
        )

        # End session
        slip = inbound_service.end_session(
            session_id=session_id,
            worker_id=worker_id,
            organization_id=org_id,
        )

        assert slip["status"] == "pending_review"
        assert slip["total_boxes"] == 2
        assert slip["total_items"] == 30
        assert slip["session_id"] == str(session_id)
        assert slip["slip_number"] is not None
        assert len(slip["items"]) == 1  # Grouped by SKU+batch
        assert slip["items"][0]["sku"] == "ITEM-A"
        assert slip["items"][0]["quantity"] == 30
        assert slip["items"][0]["box_count"] == 2

    def test_groups_items_by_sku_and_batch(
        self, inbound_service, org_id, worker_id, warehouse_id
    ):
        """Should group items by SKU and batch in the receiving slip."""
        session = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session["id"])

        # Same SKU, different batches
        inbound_service.record_scan(
            session_id=session_id,
            qr_data=_make_qr_payload(qr_id="QR-001", sku="ITEM-A", qty=10, batch="B1"),
            worker_id=worker_id,
            organization_id=org_id,
        )
        inbound_service.record_scan(
            session_id=session_id,
            qr_data=_make_qr_payload(qr_id="QR-002", sku="ITEM-A", qty=20, batch="B2"),
            worker_id=worker_id,
            organization_id=org_id,
        )
        # Different SKU
        inbound_service.record_scan(
            session_id=session_id,
            qr_data=_make_qr_payload(qr_id="QR-003", sku="ITEM-B", qty=5, batch="B1"),
            worker_id=worker_id,
            organization_id=org_id,
        )

        slip = inbound_service.end_session(
            session_id=session_id,
            worker_id=worker_id,
            organization_id=org_id,
        )

        assert slip["total_boxes"] == 3
        assert slip["total_items"] == 35
        # 3 distinct SKU+batch combinations
        assert len(slip["items"]) == 3

    def test_rejects_end_on_closed_session(
        self, inbound_service, org_id, worker_id, warehouse_id
    ):
        """Should reject ending an already closed session."""
        from app.core.exceptions import StateError

        session = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session["id"])

        inbound_service.end_session(
            session_id=session_id,
            worker_id=worker_id,
            organization_id=org_id,
        )

        with pytest.raises(StateError, match="Session is already closed"):
            inbound_service.end_session(
                session_id=session_id,
                worker_id=worker_id,
                organization_id=org_id,
            )

    def test_rejects_end_on_nonexistent_session(
        self, inbound_service, org_id, worker_id
    ):
        """Should raise NotFoundError for non-existent session."""
        from app.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError, match="Scan session not found"):
            inbound_service.end_session(
                session_id=uuid.uuid4(),
                worker_id=worker_id,
                organization_id=org_id,
            )


class TestGetSessionSummary:
    """Tests for get_session_summary method."""

    def test_returns_aggregated_summary(
        self, inbound_service, org_id, worker_id, warehouse_id
    ):
        """Should return per-SKU/batch aggregation and box count."""
        session = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session["id"])

        # Record multiple scans
        inbound_service.record_scan(
            session_id=session_id,
            qr_data=_make_qr_payload(qr_id="QR-001", sku="ITEM-A", qty=10, batch="B1"),
            worker_id=worker_id,
            organization_id=org_id,
        )
        inbound_service.record_scan(
            session_id=session_id,
            qr_data=_make_qr_payload(qr_id="QR-002", sku="ITEM-A", qty=20, batch="B1"),
            worker_id=worker_id,
            organization_id=org_id,
        )
        inbound_service.record_scan(
            session_id=session_id,
            qr_data=_make_qr_payload(qr_id="QR-003", sku="ITEM-B", qty=5, batch="B2"),
            worker_id=worker_id,
            organization_id=org_id,
        )

        summary = inbound_service.get_session_summary(
            session_id=session_id,
            organization_id=org_id,
        )

        assert summary["session_id"] == str(session_id)
        assert summary["status"] == "open"
        assert summary["total_boxes"] == 3
        assert summary["total_quantity"] == 35
        assert len(summary["items"]) == 2  # 2 distinct SKUs

        # Find ITEM-A summary
        item_a = next(i for i in summary["items"] if i["sku"] == "ITEM-A")
        assert item_a["total_quantity"] == 30
        assert item_a["total_boxes"] == 2
        assert len(item_a["batches"]) == 1
        assert item_a["batches"][0]["batch_number"] == "B1"
        assert item_a["batches"][0]["quantity"] == 30
        assert item_a["batches"][0]["box_count"] == 2

        # Find ITEM-B summary
        item_b = next(i for i in summary["items"] if i["sku"] == "ITEM-B")
        assert item_b["total_quantity"] == 5
        assert item_b["total_boxes"] == 1

    def test_empty_session_summary(
        self, inbound_service, org_id, worker_id, warehouse_id
    ):
        """Should return zero counts for an empty session."""
        session = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session["id"])

        summary = inbound_service.get_session_summary(
            session_id=session_id,
            organization_id=org_id,
        )

        assert summary["total_boxes"] == 0
        assert summary["total_quantity"] == 0
        assert summary["items"] == []

    def test_rejects_nonexistent_session(self, inbound_service, org_id):
        """Should raise NotFoundError for non-existent session."""
        from app.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError, match="Scan session not found"):
            inbound_service.get_session_summary(
                session_id=uuid.uuid4(),
                organization_id=org_id,
            )
