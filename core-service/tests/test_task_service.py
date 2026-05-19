"""Unit tests for TaskService."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.worker_task import WorkerTask
from app.services.task_service import TaskService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def worker_id():
    return uuid.uuid4()


@pytest.fixture
def reference_id():
    return uuid.uuid4()


@pytest.fixture
def task_service(db_session):
    return TaskService(db_session)


class TestCreateTask:
    """Tests for TaskService.create_task"""

    def test_creates_put_away_task(self, task_service, org_id, worker_id, reference_id):
        """Should create a put_away task with assigned status."""
        result = task_service.create_task(
            task_type="put_away",
            worker_id=worker_id,
            reference_id=reference_id,
            org_id=org_id,
        )

        assert result["task_type"] == "put_away"
        assert result["worker_id"] == str(worker_id)
        assert result["reference_id"] == str(reference_id)
        assert result["organization_id"] == str(org_id)
        assert result["status"] == "assigned"
        assert result["assigned_at"] is not None
        assert result["started_at"] is None
        assert result["completed_at"] is None

    def test_creates_pick_task(self, task_service, org_id, worker_id, reference_id):
        """Should create a pick task with assigned status."""
        result = task_service.create_task(
            task_type="pick",
            worker_id=worker_id,
            reference_id=reference_id,
            org_id=org_id,
        )

        assert result["task_type"] == "pick"
        assert result["status"] == "assigned"

    def test_rejects_invalid_task_type(self, task_service, org_id, worker_id, reference_id):
        """Should raise ValidationError for invalid task_type."""
        with pytest.raises(ValidationError) as exc_info:
            task_service.create_task(
                task_type="invalid_type",
                worker_id=worker_id,
                reference_id=reference_id,
                org_id=org_id,
            )

        assert "invalid_type" in str(exc_info.value)


class TestStartTask:
    """Tests for TaskService.start_task"""

    def test_starts_assigned_task(self, task_service, org_id, worker_id, reference_id):
        """Should transition from assigned to in_progress with started_at."""
        created = task_service.create_task(
            task_type="put_away",
            worker_id=worker_id,
            reference_id=reference_id,
            org_id=org_id,
        )
        task_id = uuid.UUID(created["id"])

        result = task_service.start_task(task_id, org_id)

        assert result["status"] == "in_progress"
        assert result["started_at"] is not None

    def test_raises_not_found_for_missing_task(self, task_service, org_id):
        """Should raise NotFoundError for non-existent task."""
        with pytest.raises(NotFoundError):
            task_service.start_task(uuid.uuid4(), org_id)

    def test_raises_state_error_for_non_assigned_task(
        self, task_service, org_id, worker_id, reference_id
    ):
        """Should raise StateError if task is not in assigned status."""
        created = task_service.create_task(
            task_type="pick",
            worker_id=worker_id,
            reference_id=reference_id,
            org_id=org_id,
        )
        task_id = uuid.UUID(created["id"])

        # Start the task first
        task_service.start_task(task_id, org_id)

        # Try to start again
        with pytest.raises(StateError) as exc_info:
            task_service.start_task(task_id, org_id)

        assert exc_info.value.current_state == "in_progress"


class TestCompleteTask:
    """Tests for TaskService.complete_task"""

    def test_completes_in_progress_task(self, task_service, org_id, worker_id, reference_id):
        """Should transition from in_progress to completed with completed_at."""
        created = task_service.create_task(
            task_type="put_away",
            worker_id=worker_id,
            reference_id=reference_id,
            org_id=org_id,
        )
        task_id = uuid.UUID(created["id"])

        task_service.start_task(task_id, org_id)
        result = task_service.complete_task(task_id, org_id)

        assert result["status"] == "completed"
        assert result["completed_at"] is not None

    def test_raises_not_found_for_missing_task(self, task_service, org_id):
        """Should raise NotFoundError for non-existent task."""
        with pytest.raises(NotFoundError):
            task_service.complete_task(uuid.uuid4(), org_id)

    def test_raises_state_error_for_assigned_task(
        self, task_service, org_id, worker_id, reference_id
    ):
        """Should raise StateError if task is still in assigned status."""
        created = task_service.create_task(
            task_type="pick",
            worker_id=worker_id,
            reference_id=reference_id,
            org_id=org_id,
        )
        task_id = uuid.UUID(created["id"])

        with pytest.raises(StateError) as exc_info:
            task_service.complete_task(task_id, org_id)

        assert exc_info.value.current_state == "assigned"

    def test_raises_state_error_for_cancelled_task(
        self, task_service, org_id, worker_id, reference_id
    ):
        """Should raise StateError if task is cancelled."""
        created = task_service.create_task(
            task_type="pick",
            worker_id=worker_id,
            reference_id=reference_id,
            org_id=org_id,
        )
        task_id = uuid.UUID(created["id"])

        task_service.cancel_task(task_id, org_id)

        with pytest.raises(StateError) as exc_info:
            task_service.complete_task(task_id, org_id)

        assert exc_info.value.current_state == "cancelled"


class TestCancelTask:
    """Tests for TaskService.cancel_task"""

    def test_cancels_assigned_task(self, task_service, org_id, worker_id, reference_id):
        """Should cancel a task in assigned status."""
        created = task_service.create_task(
            task_type="put_away",
            worker_id=worker_id,
            reference_id=reference_id,
            org_id=org_id,
        )
        task_id = uuid.UUID(created["id"])

        result = task_service.cancel_task(task_id, org_id)

        assert result["status"] == "cancelled"

    def test_cancels_in_progress_task(self, task_service, org_id, worker_id, reference_id):
        """Should cancel a task in in_progress status."""
        created = task_service.create_task(
            task_type="pick",
            worker_id=worker_id,
            reference_id=reference_id,
            org_id=org_id,
        )
        task_id = uuid.UUID(created["id"])

        task_service.start_task(task_id, org_id)
        result = task_service.cancel_task(task_id, org_id)

        assert result["status"] == "cancelled"

    def test_raises_not_found_for_missing_task(self, task_service, org_id):
        """Should raise NotFoundError for non-existent task."""
        with pytest.raises(NotFoundError):
            task_service.cancel_task(uuid.uuid4(), org_id)

    def test_raises_state_error_for_completed_task(
        self, task_service, org_id, worker_id, reference_id
    ):
        """Should raise StateError if task is already completed."""
        created = task_service.create_task(
            task_type="put_away",
            worker_id=worker_id,
            reference_id=reference_id,
            org_id=org_id,
        )
        task_id = uuid.UUID(created["id"])

        task_service.start_task(task_id, org_id)
        task_service.complete_task(task_id, org_id)

        with pytest.raises(StateError) as exc_info:
            task_service.cancel_task(task_id, org_id)

        assert exc_info.value.current_state == "completed"

    def test_raises_state_error_for_already_cancelled_task(
        self, task_service, org_id, worker_id, reference_id
    ):
        """Should raise StateError if task is already cancelled."""
        created = task_service.create_task(
            task_type="put_away",
            worker_id=worker_id,
            reference_id=reference_id,
            org_id=org_id,
        )
        task_id = uuid.UUID(created["id"])

        task_service.cancel_task(task_id, org_id)

        with pytest.raises(StateError) as exc_info:
            task_service.cancel_task(task_id, org_id)

        assert exc_info.value.current_state == "cancelled"


class TestListWorkerTasks:
    """Tests for TaskService.list_worker_tasks"""

    def test_lists_tasks_for_worker(self, task_service, org_id, worker_id, reference_id):
        """Should return tasks for the specified worker."""
        # Create multiple tasks
        task_service.create_task("put_away", worker_id, reference_id, org_id)
        task_service.create_task("pick", worker_id, uuid.uuid4(), org_id)

        result = task_service.list_worker_tasks(worker_id, org_id)

        assert len(result["tasks"]) == 2
        assert result["pagination"]["total_items"] == 2

    def test_filters_by_status(self, task_service, org_id, worker_id, reference_id):
        """Should filter tasks by status."""
        created = task_service.create_task("put_away", worker_id, reference_id, org_id)
        task_service.create_task("pick", worker_id, uuid.uuid4(), org_id)

        # Start one task
        task_service.start_task(uuid.UUID(created["id"]), org_id)

        result = task_service.list_worker_tasks(worker_id, org_id, status="in_progress")

        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["status"] == "in_progress"

    def test_filters_by_date_range(self, task_service, db_session, org_id, worker_id):
        """Should filter tasks by date range."""
        # Create a task
        task_service.create_task("put_away", worker_id, uuid.uuid4(), org_id)

        # Query with a date range that includes now
        now = datetime.now(UTC)
        result = task_service.list_worker_tasks(
            worker_id,
            org_id,
            date_from=now - timedelta(hours=1),
            date_to=now + timedelta(hours=1),
        )

        assert len(result["tasks"]) == 1

    def test_returns_empty_for_no_tasks(self, task_service, org_id, worker_id):
        """Should return empty list when worker has no tasks."""
        result = task_service.list_worker_tasks(worker_id, org_id)

        assert len(result["tasks"]) == 0
        assert result["pagination"]["total_items"] == 0

    def test_does_not_return_other_workers_tasks(
        self, task_service, org_id, worker_id, reference_id
    ):
        """Should only return tasks for the specified worker."""
        other_worker_id = uuid.uuid4()

        task_service.create_task("put_away", worker_id, reference_id, org_id)
        task_service.create_task("pick", other_worker_id, uuid.uuid4(), org_id)

        result = task_service.list_worker_tasks(worker_id, org_id)

        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["worker_id"] == str(worker_id)

    def test_pagination(self, task_service, org_id, worker_id):
        """Should paginate results correctly."""
        # Create 5 tasks
        for _ in range(5):
            task_service.create_task("put_away", worker_id, uuid.uuid4(), org_id)

        result = task_service.list_worker_tasks(worker_id, org_id, page=1, page_size=2)

        assert len(result["tasks"]) == 2
        assert result["pagination"]["total_items"] == 5
        assert result["pagination"]["total_pages"] == 3
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_prev"] is False

    def test_rejects_invalid_status_filter(self, task_service, org_id, worker_id):
        """Should raise ValidationError for invalid status filter."""
        with pytest.raises(ValidationError) as exc_info:
            task_service.list_worker_tasks(worker_id, org_id, status="invalid")

        assert "invalid" in str(exc_info.value)

    def test_does_not_return_other_org_tasks(self, task_service, org_id, worker_id, reference_id):
        """Should not return tasks from other organizations."""
        other_org_id = uuid.uuid4()

        task_service.create_task("put_away", worker_id, reference_id, org_id)
        task_service.create_task("pick", worker_id, uuid.uuid4(), other_org_id)

        result = task_service.list_worker_tasks(worker_id, org_id)

        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["organization_id"] == str(org_id)
