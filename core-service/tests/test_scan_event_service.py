"""Unit tests for ScanEventService."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import ValidationError
from app.models.qr_scan_event import QRScanEvent
from app.services.scan_event_service import ScanEventService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def worker_id():
    return uuid.uuid4()


@pytest.fixture
def session_id():
    return uuid.uuid4()


@pytest.fixture
def pick_list_id():
    return uuid.uuid4()


@pytest.fixture
def scan_event_service(db_session):
    return ScanEventService(db_session)


class TestRecordEvent:
    """Tests for ScanEventService.record_event"""

    def test_records_inbound_scan_event(self, scan_event_service, org_id, worker_id, session_id):
        """Should record an inbound scan event with context in extra_data."""
        result = scan_event_service.record_event(
            organization_id=org_id,
            worker_id=worker_id,
            scan_context="inbound",
            serial_number="QR-001",
            session_id=session_id,
            decoded_payload={"id": "QR-001", "sku": "ITEM-001", "qty": 10, "batch": "B001"},
            device_type="mobile",
            os="Android 14",
        )

        assert result["organization_id"] == str(org_id)
        assert result["serial_number"] == "QR-001"
        assert result["device_type"] == "mobile"
        assert result["os"] == "Android 14"
        assert result["extra_data"]["scan_context"] == "inbound"
        assert result["extra_data"]["worker_id"] == str(worker_id)
        assert result["extra_data"]["session_id"] == str(session_id)
        assert result["extra_data"]["decoded_payload"]["sku"] == "ITEM-001"
        assert result["extra_data"]["device_type"] == "mobile"
        assert result["extra_data"]["os"] == "Android 14"
        assert result["scan_timestamp"] is not None
        assert result["id"] is not None

    def test_records_pick_scan_event(self, scan_event_service, org_id, worker_id, pick_list_id):
        """Should record a pick scan event with pick_list_id in extra_data."""
        result = scan_event_service.record_event(
            organization_id=org_id,
            worker_id=worker_id,
            scan_context="pick",
            serial_number="QR-002",
            pick_list_id=pick_list_id,
            decoded_payload={"id": "QR-002", "sku": "ITEM-002", "qty": 5, "batch": "B002"},
        )

        assert result["extra_data"]["scan_context"] == "pick"
        assert result["extra_data"]["pick_list_id"] == str(pick_list_id)
        assert result["extra_data"]["worker_id"] == str(worker_id)

    def test_records_gate_scan_event(self, scan_event_service, org_id, worker_id, session_id, pick_list_id):
        """Should record a gate scan event with both session_id and pick_list_id."""
        result = scan_event_service.record_event(
            organization_id=org_id,
            worker_id=worker_id,
            scan_context="gate",
            serial_number="QR-003",
            session_id=session_id,
            pick_list_id=pick_list_id,
            decoded_payload={"id": "QR-003", "sku": "ITEM-003", "qty": 20, "batch": "B003"},
            device_type="tablet",
            os="iOS 17",
        )

        assert result["extra_data"]["scan_context"] == "gate"
        assert result["extra_data"]["session_id"] == str(session_id)
        assert result["extra_data"]["pick_list_id"] == str(pick_list_id)
        assert result["device_type"] == "tablet"
        assert result["os"] == "iOS 17"

    def test_records_event_with_geo_data(self, scan_event_service, org_id, worker_id):
        """Should record scan event with geographic data."""
        result = scan_event_service.record_event(
            organization_id=org_id,
            worker_id=worker_id,
            scan_context="inbound",
            serial_number="QR-004",
            ip_address="192.168.1.100",
            latitude=28.6139,
            longitude=77.2090,
            city="New Delhi",
            state="Delhi",
            country="India",
        )

        assert result["ip_address"] == "192.168.1.100"
        assert result["latitude"] == 28.6139
        assert result["longitude"] == 77.209
        assert result["city"] == "New Delhi"
        assert result["state"] == "Delhi"
        assert result["country"] == "India"

    def test_records_event_with_minimal_data(self, scan_event_service, org_id, worker_id):
        """Should record scan event with only required fields."""
        result = scan_event_service.record_event(
            organization_id=org_id,
            worker_id=worker_id,
            scan_context="inbound",
        )

        assert result["organization_id"] == str(org_id)
        assert result["extra_data"]["scan_context"] == "inbound"
        assert result["extra_data"]["worker_id"] == str(worker_id)
        assert result["serial_number"] is None
        assert result["device_type"] is None
        assert result["os"] is None

    def test_rejects_invalid_scan_context(self, scan_event_service, org_id, worker_id):
        """Should raise ValidationError for invalid scan_context."""
        with pytest.raises(ValidationError) as exc_info:
            scan_event_service.record_event(
                organization_id=org_id,
                worker_id=worker_id,
                scan_context="invalid_context",
            )

        assert "invalid_context" in str(exc_info.value)


class TestQueryEvents:
    """Tests for ScanEventService.query_events"""

    def _create_events(self, scan_event_service, org_id, worker_id, session_id):
        """Helper to create multiple scan events for testing queries."""
        events = []
        for i in range(5):
            event = scan_event_service.record_event(
                organization_id=org_id,
                worker_id=worker_id,
                scan_context="inbound",
                serial_number=f"QR-{i:03d}",
                session_id=session_id,
                decoded_payload={"id": f"QR-{i:03d}", "sku": f"ITEM-{i:03d}", "qty": i + 1, "batch": "B001"},
            )
            events.append(event)
        return events

    def test_queries_all_events_for_org(self, scan_event_service, org_id, worker_id, session_id):
        """Should return all scan events for the organization."""
        self._create_events(scan_event_service, org_id, worker_id, session_id)

        result = scan_event_service.query_events(organization_id=org_id)

        assert len(result["scan_events"]) == 5
        assert result["pagination"]["total_items"] == 5
        assert result["pagination"]["page"] == 1

    def test_filters_by_session_id(self, scan_event_service, org_id, worker_id):
        """Should filter events by session_id."""
        session_a = uuid.uuid4()
        session_b = uuid.uuid4()

        # Create events for session A
        for i in range(3):
            scan_event_service.record_event(
                organization_id=org_id,
                worker_id=worker_id,
                scan_context="inbound",
                serial_number=f"QR-A{i}",
                session_id=session_a,
            )

        # Create events for session B
        for i in range(2):
            scan_event_service.record_event(
                organization_id=org_id,
                worker_id=worker_id,
                scan_context="gate",
                serial_number=f"QR-B{i}",
                session_id=session_b,
            )

        result = scan_event_service.query_events(
            organization_id=org_id,
            session_id=session_a,
        )

        assert len(result["scan_events"]) == 3

    def test_filters_by_worker_id(self, scan_event_service, org_id):
        """Should filter events by worker_id."""
        worker_a = uuid.uuid4()
        worker_b = uuid.uuid4()

        # Create events for worker A
        for i in range(4):
            scan_event_service.record_event(
                organization_id=org_id,
                worker_id=worker_a,
                scan_context="inbound",
                serial_number=f"QR-WA{i}",
            )

        # Create events for worker B
        for i in range(2):
            scan_event_service.record_event(
                organization_id=org_id,
                worker_id=worker_b,
                scan_context="pick",
                serial_number=f"QR-WB{i}",
            )

        result = scan_event_service.query_events(
            organization_id=org_id,
            worker_id=worker_a,
        )

        assert len(result["scan_events"]) == 4

    def test_filters_by_scan_context(self, scan_event_service, org_id, worker_id):
        """Should filter events by scan_context."""
        # Create inbound events
        for i in range(3):
            scan_event_service.record_event(
                organization_id=org_id,
                worker_id=worker_id,
                scan_context="inbound",
                serial_number=f"QR-IN{i}",
            )

        # Create pick events
        for i in range(2):
            scan_event_service.record_event(
                organization_id=org_id,
                worker_id=worker_id,
                scan_context="pick",
                serial_number=f"QR-PK{i}",
            )

        result = scan_event_service.query_events(
            organization_id=org_id,
            scan_context="pick",
        )

        assert len(result["scan_events"]) == 2

    def test_filters_by_date_range(self, scan_event_service, db_session, org_id, worker_id):
        """Should filter events by date range."""
        now = datetime.now(UTC)

        # Create an event and manually set its timestamp to the past
        event = QRScanEvent(
            organization_id=org_id,
            serial_number="QR-OLD",
            scan_timestamp=now - timedelta(days=10),
            extra_data={"scan_context": "inbound", "worker_id": str(worker_id)},
        )
        db_session.add(event)
        db_session.commit()

        # Create a recent event
        scan_event_service.record_event(
            organization_id=org_id,
            worker_id=worker_id,
            scan_context="inbound",
            serial_number="QR-NEW",
        )

        # Query for events in the last 5 days
        result = scan_event_service.query_events(
            organization_id=org_id,
            date_from=now - timedelta(days=5),
        )

        assert len(result["scan_events"]) == 1
        assert result["scan_events"][0]["serial_number"] == "QR-NEW"

    def test_filters_by_serial_number(self, scan_event_service, org_id, worker_id):
        """Should filter events by serial_number."""
        scan_event_service.record_event(
            organization_id=org_id,
            worker_id=worker_id,
            scan_context="inbound",
            serial_number="QR-UNIQUE-001",
        )
        scan_event_service.record_event(
            organization_id=org_id,
            worker_id=worker_id,
            scan_context="inbound",
            serial_number="QR-OTHER-002",
        )

        result = scan_event_service.query_events(
            organization_id=org_id,
            serial_number="QR-UNIQUE-001",
        )

        assert len(result["scan_events"]) == 1
        assert result["scan_events"][0]["serial_number"] == "QR-UNIQUE-001"

    def test_pagination(self, scan_event_service, org_id, worker_id):
        """Should paginate results correctly."""
        # Create 15 events
        for i in range(15):
            scan_event_service.record_event(
                organization_id=org_id,
                worker_id=worker_id,
                scan_context="inbound",
                serial_number=f"QR-PAGE-{i:03d}",
            )

        # Get first page
        result = scan_event_service.query_events(
            organization_id=org_id,
            page=1,
            page_size=10,
        )

        assert len(result["scan_events"]) == 10
        assert result["pagination"]["total_items"] == 15
        assert result["pagination"]["total_pages"] == 2
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_prev"] is False

        # Get second page
        result = scan_event_service.query_events(
            organization_id=org_id,
            page=2,
            page_size=10,
        )

        assert len(result["scan_events"]) == 5
        assert result["pagination"]["has_next"] is False
        assert result["pagination"]["has_prev"] is True

    def test_does_not_return_other_org_events(self, scan_event_service, org_id, worker_id):
        """Should not return events from other organizations."""
        other_org_id = uuid.uuid4()

        scan_event_service.record_event(
            organization_id=org_id,
            worker_id=worker_id,
            scan_context="inbound",
            serial_number="QR-ORG-A",
        )
        scan_event_service.record_event(
            organization_id=other_org_id,
            worker_id=worker_id,
            scan_context="inbound",
            serial_number="QR-ORG-B",
        )

        result = scan_event_service.query_events(organization_id=org_id)

        assert len(result["scan_events"]) == 1
        assert result["scan_events"][0]["serial_number"] == "QR-ORG-A"

    def test_orders_by_most_recent_first(self, scan_event_service, db_session, org_id, worker_id):
        """Should return events ordered by scan_timestamp descending."""
        now = datetime.now(UTC)

        # Create events with different timestamps
        for i in range(3):
            event = QRScanEvent(
                organization_id=org_id,
                serial_number=f"QR-ORDER-{i}",
                scan_timestamp=now - timedelta(hours=i),
                extra_data={"scan_context": "inbound", "worker_id": str(worker_id)},
            )
            db_session.add(event)
        db_session.commit()

        result = scan_event_service.query_events(organization_id=org_id)

        # Most recent first
        assert result["scan_events"][0]["serial_number"] == "QR-ORDER-0"
        assert result["scan_events"][1]["serial_number"] == "QR-ORDER-1"
        assert result["scan_events"][2]["serial_number"] == "QR-ORDER-2"

    def test_rejects_invalid_scan_context_filter(self, scan_event_service, org_id):
        """Should raise ValidationError for invalid scan_context filter."""
        with pytest.raises(ValidationError) as exc_info:
            scan_event_service.query_events(
                organization_id=org_id,
                scan_context="invalid",
            )

        assert "invalid" in str(exc_info.value)

    def test_returns_empty_for_no_events(self, scan_event_service, org_id):
        """Should return empty list when no events match."""
        result = scan_event_service.query_events(organization_id=org_id)

        assert len(result["scan_events"]) == 0
        assert result["pagination"]["total_items"] == 0
        assert result["pagination"]["total_pages"] == 1
