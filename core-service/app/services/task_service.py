"""Task service for managing worker task assignments.

Manages put-away and pick tasks assigned to warehouse workers, including
status transitions and filtered listing.

Provides:
- create_task: Create a worker task (put_away or pick)
- start_task: Transition ASSIGNED → IN_PROGRESS with started_at
- complete_task: Transition IN_PROGRESS → COMPLETED with completed_at
- cancel_task: Cancel from ASSIGNED or IN_PROGRESS
- list_worker_tasks: List tasks with filters (worker_id, status, date range)

Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.worker_task import WorkerTask


# Valid task types
VALID_TASK_TYPES = ("put_away", "pick")

# Valid status transitions
VALID_STATUSES = ("assigned", "in_progress", "completed", "cancelled")


class TaskService:
    """Service for managing worker task assignments for put-away and pick operations."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # CREATE TASK
    # ------------------------------------------------------------------

    def create_task(
        self,
        task_type: str,
        worker_id: UUID,
        reference_id: UUID,
        org_id: UUID,
    ) -> dict:
        """Create a worker task record.

        Args:
            task_type: Type of task - 'put_away' or 'pick'.
            worker_id: UUID of the worker assigned to the task.
            reference_id: UUID of the put_away_list or pick_list.
            org_id: Organization UUID for tenant isolation.

        Returns:
            Dictionary representation of the created WorkerTask.

        Raises:
            ValidationError: If task_type is invalid.

        Requirements: 16.1, 16.2
        """
        if task_type not in VALID_TASK_TYPES:
            raise ValidationError(
                message=f"Invalid task_type '{task_type}'. Must be one of: {', '.join(VALID_TASK_TYPES)}",
                details=[
                    {
                        "field": "task_type",
                        "reason": f"Must be one of: {', '.join(VALID_TASK_TYPES)}",
                    }
                ],
            )

        now = datetime.now(UTC)
        task = WorkerTask(
            organization_id=org_id,
            task_type=task_type,
            worker_id=worker_id,
            reference_id=reference_id,
            status="assigned",
            assigned_at=now,
            created_at=now,
            updated_at=now,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        return self._task_to_dict(task)

    # ------------------------------------------------------------------
    # START TASK
    # ------------------------------------------------------------------

    def start_task(self, task_id: UUID, org_id: UUID) -> dict:
        """Transition a task from ASSIGNED to IN_PROGRESS.

        Records the started_at timestamp.

        Args:
            task_id: UUID of the task to start.
            org_id: Organization UUID for tenant isolation.

        Returns:
            Dictionary representation of the updated WorkerTask.

        Raises:
            NotFoundError: If task is not found.
            StateError: If task is not in ASSIGNED status.

        Requirements: 16.4
        """
        task = self._get_task(task_id, org_id)

        if task.status != "assigned":
            raise StateError(
                message="Task must be in 'assigned' status to start",
                current_state=task.status,
                required_state=["assigned"],
            )

        task.status = "in_progress"
        task.started_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(task)

        return self._task_to_dict(task)

    # ------------------------------------------------------------------
    # COMPLETE TASK
    # ------------------------------------------------------------------

    def complete_task(self, task_id: UUID, org_id: UUID) -> dict:
        """Transition a task from IN_PROGRESS to COMPLETED.

        Records the completed_at timestamp.

        Args:
            task_id: UUID of the task to complete.
            org_id: Organization UUID for tenant isolation.

        Returns:
            Dictionary representation of the updated WorkerTask.

        Raises:
            NotFoundError: If task is not found.
            StateError: If task is not in IN_PROGRESS status.

        Requirements: 16.5
        """
        task = self._get_task(task_id, org_id)

        if task.status != "in_progress":
            raise StateError(
                message="Task must be in 'in_progress' status to complete",
                current_state=task.status,
                required_state=["in_progress"],
            )

        task.status = "completed"
        task.completed_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(task)

        return self._task_to_dict(task)

    # ------------------------------------------------------------------
    # CANCEL TASK
    # ------------------------------------------------------------------

    def cancel_task(self, task_id: UUID, org_id: UUID) -> dict:
        """Cancel a task from ASSIGNED or IN_PROGRESS status.

        Args:
            task_id: UUID of the task to cancel.
            org_id: Organization UUID for tenant isolation.

        Returns:
            Dictionary representation of the updated WorkerTask.

        Raises:
            NotFoundError: If task is not found.
            StateError: If task is not in ASSIGNED or IN_PROGRESS status.

        Requirements: 16.3
        """
        task = self._get_task(task_id, org_id)

        if task.status not in ("assigned", "in_progress"):
            raise StateError(
                message="Task must be in 'assigned' or 'in_progress' status to cancel",
                current_state=task.status,
                required_state=["assigned", "in_progress"],
            )

        task.status = "cancelled"
        task.updated_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(task)

        return self._task_to_dict(task)

    # ------------------------------------------------------------------
    # LIST WORKER TASKS
    # ------------------------------------------------------------------

    def list_worker_tasks(
        self,
        worker_id: UUID,
        org_id: UUID,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List tasks for a specific worker with optional filters.

        Args:
            worker_id: UUID of the worker whose tasks to list.
            org_id: Organization UUID for tenant isolation.
            status: Optional status filter (assigned, in_progress, completed, cancelled).
            date_from: Optional start date filter (inclusive).
            date_to: Optional end date filter (inclusive).
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with tasks list and pagination info.

        Raises:
            ValidationError: If status filter is invalid.

        Requirements: 16.6
        """
        if status and status not in VALID_STATUSES:
            raise ValidationError(
                message=f"Invalid status filter '{status}'. Must be one of: {', '.join(VALID_STATUSES)}",
                details=[
                    {
                        "field": "status",
                        "reason": f"Must be one of: {', '.join(VALID_STATUSES)}",
                    }
                ],
            )

        # Build query filters
        filters = [
            WorkerTask.organization_id == org_id,
            WorkerTask.worker_id == worker_id,
        ]

        if status:
            filters.append(WorkerTask.status == status)

        if date_from:
            filters.append(WorkerTask.assigned_at >= date_from)

        if date_to:
            filters.append(WorkerTask.assigned_at <= date_to)

        # Get total count
        total_items = self.db.query(WorkerTask).filter(and_(*filters)).count()

        # Calculate pagination
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        offset = (page - 1) * page_size

        # Fetch tasks with pagination
        tasks = (
            self.db.query(WorkerTask)
            .filter(and_(*filters))
            .order_by(WorkerTask.assigned_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return {
            "tasks": [self._task_to_dict(task) for task in tasks],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _get_task(self, task_id: UUID, org_id: UUID) -> WorkerTask:
        """Fetch a task by ID and organization, raising NotFoundError if missing."""
        task = (
            self.db.query(WorkerTask)
            .filter(
                WorkerTask.id == task_id,
                WorkerTask.organization_id == org_id,
            )
            .first()
        )

        if task is None:
            raise NotFoundError(
                message="Worker task not found",
                entity_type="WorkerTask",
                entity_id=str(task_id),
            )

        return task

    def _task_to_dict(self, task: WorkerTask) -> dict:
        """Convert a WorkerTask model to a dictionary."""
        return {
            "id": str(task.id),
            "organization_id": str(task.organization_id),
            "task_type": task.task_type,
            "worker_id": str(task.worker_id),
            "reference_id": str(task.reference_id),
            "status": task.status,
            "assigned_at": task.assigned_at.isoformat() if task.assigned_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }
