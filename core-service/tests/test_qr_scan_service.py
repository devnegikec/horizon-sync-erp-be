"""Unit tests for QRScanService (location time tracking)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.models.location_scan import LocationScan
from app.models.worker_task import WorkerTask
from app.services.qr_scan_service import QRScanService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def worker_id():
    return uuid.uuid4()


@pytest.fixture
def worker_task(db_session, org_id, worker_id):
    """Create a worker task for testing."""
    task = WorkerTask(
        id=uuid.uuid4(),
        organization_id=org_id,
        task_type="put_away",
        worker_id=worker_id,
        reference_id=uuid.uuid4(),
        status="in_progress",
        assigned_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def qr_scan_service(db_session):
    return QRScanService(db_session)


class TestRecordLocationScan:
    """Tests for record_location_scan method."""

    def test_records_start_scan_successfully(
        self, qr_scan_service, org_id, worker_task
    ):
        """Should create a start scan record with no elapsed_seconds."""
        result = qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A03-B02-L04-B01",
            scan_type="start",
            org_id=org_id,
        )

        assert result["scan_type"] == "start"
        assert result["location_code"] == "Z01-A03-B02-L04-B01"
        assert result["worker_task_id"] == str(worker_task.id)
        assert result["elapsed_seconds"] is None
        assert result["scanned_at"] is not None

    def test_records_finish_scan_with_elapsed_seconds(
        self, qr_scan_service, org_id, worker_task
    ):
        """Should calculate elapsed_seconds on a finish scan."""
        start_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        finish_time = datetime(2025, 1, 15, 10, 5, 30, tzinfo=UTC)

        # Record start scan
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A03-B02-L04-B01",
            scan_type="start",
            org_id=org_id,
            scanned_at=start_time,
        )

        # Record finish scan
        result = qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A03-B02-L04-B01",
            scan_type="finish",
            org_id=org_id,
            scanned_at=finish_time,
        )

        assert result["scan_type"] == "finish"
        assert result["elapsed_seconds"] == 330  # 5 minutes 30 seconds

    def test_rejects_finish_scan_without_preceding_start(
        self, qr_scan_service, org_id, worker_task
    ):
        """Should raise ValidationError when finish scan has no preceding start."""
        with pytest.raises(ValidationError) as exc_info:
            qr_scan_service.record_location_scan(
                worker_id=worker_task.worker_id,
                task_id=worker_task.id,
                location_code="Z01-A03-B02-L04-B01",
                scan_type="finish",
                org_id=org_id,
            )
        assert "no preceding start scan" in str(exc_info.value).lower()

    def test_rejects_invalid_scan_type(
        self, qr_scan_service, org_id, worker_task
    ):
        """Should raise ValidationError for invalid scan_type."""
        with pytest.raises(ValidationError) as exc_info:
            qr_scan_service.record_location_scan(
                worker_id=worker_task.worker_id,
                task_id=worker_task.id,
                location_code="Z01-A03-B02-L04-B01",
                scan_type="invalid",
                org_id=org_id,
            )
        assert "invalid scan_type" in str(exc_info.value).lower()

    def test_raises_not_found_for_missing_task(
        self, qr_scan_service, org_id, worker_id
    ):
        """Should raise NotFoundError if worker task doesn't exist."""
        with pytest.raises(NotFoundError) as exc_info:
            qr_scan_service.record_location_scan(
                worker_id=worker_id,
                task_id=uuid.uuid4(),
                location_code="Z01-A03-B02-L04-B01",
                scan_type="start",
                org_id=org_id,
            )
        assert "Worker task not found" in str(exc_info.value)

    def test_finish_scan_uses_most_recent_start(
        self, qr_scan_service, org_id, worker_task
    ):
        """Should use the most recent start scan when calculating elapsed."""
        first_start = datetime(2025, 1, 15, 9, 0, 0, tzinfo=UTC)
        second_start = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        finish_time = datetime(2025, 1, 15, 10, 2, 0, tzinfo=UTC)

        # Record two start scans
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A03-B02-L04-B01",
            scan_type="start",
            org_id=org_id,
            scanned_at=first_start,
        )
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A03-B02-L04-B01",
            scan_type="start",
            org_id=org_id,
            scanned_at=second_start,
        )

        # Finish scan should use the most recent start (10:00)
        result = qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A03-B02-L04-B01",
            scan_type="finish",
            org_id=org_id,
            scanned_at=finish_time,
        )

        # 10:02 - 10:00 = 120 seconds
        assert result["elapsed_seconds"] == 120

    def test_different_locations_are_independent(
        self, qr_scan_service, org_id, worker_task
    ):
        """A finish scan at location B should not find a start scan at location A."""
        # Start scan at location A
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B01",
            scan_type="start",
            org_id=org_id,
        )

        # Finish scan at location B should fail (no start at B)
        with pytest.raises(ValidationError):
            qr_scan_service.record_location_scan(
                worker_id=worker_task.worker_id,
                task_id=worker_task.id,
                location_code="Z01-A01-B01-L01-B02",
                scan_type="finish",
                org_id=org_id,
            )


class TestGetTimeSummary:
    """Tests for get_time_summary method."""

    def test_returns_empty_summary_with_no_data(
        self, qr_scan_service, org_id
    ):
        """Should return zero totals when no finish scans exist."""
        result = qr_scan_service.get_time_summary(org_id=org_id)

        assert result["total_elapsed_seconds"] == 0
        assert result["total_scans"] == 0
        assert result["avg_elapsed_seconds"] == 0
        assert result["by_location"] == []
        assert result["records"] == []

    def test_returns_summary_with_finish_scans(
        self, qr_scan_service, org_id, worker_task
    ):
        """Should aggregate elapsed_seconds from finish scans."""
        start1 = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        finish1 = datetime(2025, 1, 15, 10, 5, 0, tzinfo=UTC)
        start2 = datetime(2025, 1, 15, 10, 10, 0, tzinfo=UTC)
        finish2 = datetime(2025, 1, 15, 10, 13, 0, tzinfo=UTC)

        # Record two start/finish pairs at different locations
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B01",
            scan_type="start",
            org_id=org_id,
            scanned_at=start1,
        )
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B01",
            scan_type="finish",
            org_id=org_id,
            scanned_at=finish1,
        )
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B02",
            scan_type="start",
            org_id=org_id,
            scanned_at=start2,
        )
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B02",
            scan_type="finish",
            org_id=org_id,
            scanned_at=finish2,
        )

        result = qr_scan_service.get_time_summary(org_id=org_id)

        assert result["total_elapsed_seconds"] == 480  # 300 + 180
        assert result["total_scans"] == 2
        assert result["avg_elapsed_seconds"] == 240.0
        assert len(result["by_location"]) == 2
        assert len(result["records"]) == 2

    def test_filters_by_worker_id(
        self, qr_scan_service, db_session, org_id, worker_task
    ):
        """Should filter results by worker_id."""
        # Create a second worker task with a different worker
        other_worker_id = uuid.uuid4()
        other_task = WorkerTask(
            id=uuid.uuid4(),
            organization_id=org_id,
            task_type="pick",
            worker_id=other_worker_id,
            reference_id=uuid.uuid4(),
            status="in_progress",
            assigned_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
        )
        db_session.add(other_task)
        db_session.commit()
        db_session.refresh(other_task)

        start_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        finish_time = datetime(2025, 1, 15, 10, 5, 0, tzinfo=UTC)

        # Record scans for both workers
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B01",
            scan_type="start",
            org_id=org_id,
            scanned_at=start_time,
        )
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B01",
            scan_type="finish",
            org_id=org_id,
            scanned_at=finish_time,
        )
        qr_scan_service.record_location_scan(
            worker_id=other_worker_id,
            task_id=other_task.id,
            location_code="Z01-A01-B01-L01-B02",
            scan_type="start",
            org_id=org_id,
            scanned_at=start_time,
        )
        qr_scan_service.record_location_scan(
            worker_id=other_worker_id,
            task_id=other_task.id,
            location_code="Z01-A01-B01-L01-B02",
            scan_type="finish",
            org_id=org_id,
            scanned_at=finish_time,
        )

        # Filter by first worker
        result = qr_scan_service.get_time_summary(
            org_id=org_id,
            worker_id=worker_task.worker_id,
        )

        assert result["total_scans"] == 1
        assert result["total_elapsed_seconds"] == 300

    def test_filters_by_task_id(
        self, qr_scan_service, org_id, worker_task
    ):
        """Should filter results by task_id."""
        start_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        finish_time = datetime(2025, 1, 15, 10, 5, 0, tzinfo=UTC)

        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B01",
            scan_type="start",
            org_id=org_id,
            scanned_at=start_time,
        )
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B01",
            scan_type="finish",
            org_id=org_id,
            scanned_at=finish_time,
        )

        # Filter by the task
        result = qr_scan_service.get_time_summary(
            org_id=org_id,
            task_id=worker_task.id,
        )

        assert result["total_scans"] == 1
        assert result["total_elapsed_seconds"] == 300

        # Filter by a non-existent task
        result = qr_scan_service.get_time_summary(
            org_id=org_id,
            task_id=uuid.uuid4(),
        )

        assert result["total_scans"] == 0

    def test_filters_by_location_code(
        self, qr_scan_service, org_id, worker_task
    ):
        """Should filter results by location_code."""
        start_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        finish_time = datetime(2025, 1, 15, 10, 5, 0, tzinfo=UTC)

        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B01",
            scan_type="start",
            org_id=org_id,
            scanned_at=start_time,
        )
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B01",
            scan_type="finish",
            org_id=org_id,
            scanned_at=finish_time,
        )

        # Filter by location
        result = qr_scan_service.get_time_summary(
            org_id=org_id,
            location_code="Z01-A01-B01-L01-B01",
        )
        assert result["total_scans"] == 1

        # Filter by non-existent location
        result = qr_scan_service.get_time_summary(
            org_id=org_id,
            location_code="Z99-A99-B99-L99-B99",
        )
        assert result["total_scans"] == 0

    def test_filters_by_date_range(
        self, qr_scan_service, org_id, worker_task
    ):
        """Should filter results by date range."""
        from datetime import date

        jan_15_start = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        jan_15_finish = datetime(2025, 1, 15, 10, 5, 0, tzinfo=UTC)
        jan_20_start = datetime(2025, 1, 20, 10, 0, 0, tzinfo=UTC)
        jan_20_finish = datetime(2025, 1, 20, 10, 3, 0, tzinfo=UTC)

        # Record scans on Jan 15
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B01",
            scan_type="start",
            org_id=org_id,
            scanned_at=jan_15_start,
        )
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B01",
            scan_type="finish",
            org_id=org_id,
            scanned_at=jan_15_finish,
        )

        # Record scans on Jan 20
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B02",
            scan_type="start",
            org_id=org_id,
            scanned_at=jan_20_start,
        )
        qr_scan_service.record_location_scan(
            worker_id=worker_task.worker_id,
            task_id=worker_task.id,
            location_code="Z01-A01-B01-L01-B02",
            scan_type="finish",
            org_id=org_id,
            scanned_at=jan_20_finish,
        )

        # Filter to only Jan 15
        result = qr_scan_service.get_time_summary(
            org_id=org_id,
            date_from=date(2025, 1, 15),
            date_to=date(2025, 1, 15),
        )
        assert result["total_scans"] == 1
        assert result["total_elapsed_seconds"] == 300

        # Filter to only Jan 20
        result = qr_scan_service.get_time_summary(
            org_id=org_id,
            date_from=date(2025, 1, 20),
            date_to=date(2025, 1, 20),
        )
        assert result["total_scans"] == 1
        assert result["total_elapsed_seconds"] == 180

        # Filter to full range
        result = qr_scan_service.get_time_summary(
            org_id=org_id,
            date_from=date(2025, 1, 15),
            date_to=date(2025, 1, 20),
        )
        assert result["total_scans"] == 2
        assert result["total_elapsed_seconds"] == 480
