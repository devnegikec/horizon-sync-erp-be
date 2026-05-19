"""Worker Tasks API endpoints.

Manages worker task assignments for put-away and pick operations:
- Create a worker task
- List worker tasks with filters (worker_id, status, date range)
- Get task detail
- Start a task (ASSIGNED → IN_PROGRESS)
- Complete a task (IN_PROGRESS → COMPLETED)
- Cancel a task

Requirements: 16.6
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import PICK_LIST_CREATE, PICK_LIST_READ, PICK_LIST_UPDATE
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.worker_task import (
    WorkerTaskCreate,
    WorkerTaskListResponse,
    WorkerTaskResponse,
)
from app.services.task_service import TaskService

router = APIRouter()


@router.post(
    "",
    response_model=WorkerTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a worker task",
    description="Create a new worker task for put-away or pick operations",
)
async def create_worker_task(
    data: WorkerTaskCreate,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Create a worker task.

    Creates a new task record with status ASSIGNED and records the
    assigned_at timestamp.

    **Request Body:**
    - **task_type**: Type of task - 'put_away' or 'pick'
    - **worker_id**: UUID of the worker assigned to the task
    - **reference_id**: UUID of the put_away_list or pick_list

    **Returns:** Created worker task

    Requirements: 16.1, 16.2
    """
    service = TaskService(db)

    result = service.create_task(
        task_type=data.task_type,
        worker_id=data.worker_id,
        reference_id=data.reference_id,
        org_id=current_user.organization_id,
    )

    return WorkerTaskResponse(**result)


@router.get(
    "",
    response_model=WorkerTaskListResponse,
    summary="List worker tasks",
    description="List worker tasks with filters for worker_id, status, and date range",
)
async def list_worker_tasks(
    worker_id: UUID = Query(..., description="Worker UUID to list tasks for"),
    task_status: str | None = Query(
        None,
        alias="status",
        description="Filter by status: assigned, in_progress, completed, cancelled",
    ),
    date_from: datetime | None = Query(
        None, description="Filter tasks assigned from this date (inclusive)"
    ),
    date_to: datetime | None = Query(
        None, description="Filter tasks assigned up to this date (inclusive)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    """
    List worker tasks with filters and pagination.

    Returns tasks for a specific worker, optionally filtered by status
    and date range. Results are ordered by assigned_at descending.

    **Query Parameters:**
    - **worker_id**: (required) Worker UUID to list tasks for
    - **status**: Filter by task status
    - **date_from**: Filter tasks assigned from this date (inclusive)
    - **date_to**: Filter tasks assigned up to this date (inclusive)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)

    **Returns:** Paginated list of worker tasks

    Requirements: 16.6
    """
    service = TaskService(db)

    result = service.list_worker_tasks(
        worker_id=worker_id,
        org_id=current_user.organization_id,
        status=task_status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )

    return WorkerTaskListResponse(**result)


@router.get(
    "/{task_id}",
    response_model=WorkerTaskResponse,
    summary="Get worker task detail",
    description="Get a single worker task by ID",
)
async def get_worker_task(
    task_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    """
    Get worker task detail.

    Returns the full worker task record including status and timestamps.

    **Path Parameters:**
    - **task_id**: UUID of the worker task

    **Returns:** Worker task detail

    Requirements: 16.6
    """
    service = TaskService(db)

    # Use the internal _get_task and _task_to_dict methods
    task = service._get_task(task_id, current_user.organization_id)
    result = service._task_to_dict(task)

    return WorkerTaskResponse(**result)


@router.post(
    "/{task_id}/start",
    response_model=WorkerTaskResponse,
    summary="Start a worker task",
    description="Transition a task from ASSIGNED to IN_PROGRESS",
)
async def start_worker_task(
    task_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Start a worker task.

    Transitions the task from ASSIGNED to IN_PROGRESS and records
    the started_at timestamp.

    **Path Parameters:**
    - **task_id**: UUID of the worker task to start

    **Returns:** Updated worker task with IN_PROGRESS status

    Requirements: 16.4
    """
    service = TaskService(db)

    result = service.start_task(
        task_id=task_id,
        org_id=current_user.organization_id,
    )

    return WorkerTaskResponse(**result)


@router.post(
    "/{task_id}/complete",
    response_model=WorkerTaskResponse,
    summary="Complete a worker task",
    description="Transition a task from IN_PROGRESS to COMPLETED",
)
async def complete_worker_task(
    task_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Complete a worker task.

    Transitions the task from IN_PROGRESS to COMPLETED and records
    the completed_at timestamp.

    **Path Parameters:**
    - **task_id**: UUID of the worker task to complete

    **Returns:** Updated worker task with COMPLETED status

    Requirements: 16.5
    """
    service = TaskService(db)

    result = service.complete_task(
        task_id=task_id,
        org_id=current_user.organization_id,
    )

    return WorkerTaskResponse(**result)


@router.post(
    "/{task_id}/cancel",
    response_model=WorkerTaskResponse,
    summary="Cancel a worker task",
    description="Cancel a task from ASSIGNED or IN_PROGRESS status",
)
async def cancel_worker_task(
    task_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Cancel a worker task.

    Cancels the task from ASSIGNED or IN_PROGRESS status.

    **Path Parameters:**
    - **task_id**: UUID of the worker task to cancel

    **Returns:** Updated worker task with CANCELLED status

    Requirements: 16.3
    """
    service = TaskService(db)

    result = service.cancel_task(
        task_id=task_id,
        org_id=current_user.organization_id,
    )

    return WorkerTaskResponse(**result)
