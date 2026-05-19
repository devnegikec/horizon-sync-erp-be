"""Pydantic schemas for worker task endpoints.

Handles worker task management:
- Create worker tasks (put_away or pick)
- List worker tasks with filters (worker_id, status, date range)
- Get task detail
- Start, complete, cancel tasks

Requirements: 16.6
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import PaginationMeta

# ===========================================
# REQUEST SCHEMAS
# ===========================================


class WorkerTaskCreate(BaseModel):
    """Request schema for creating a worker task.

    Requirements: 16.1, 16.2
    """

    task_type: str = Field(
        ...,
        description="Type of task: 'put_away' or 'pick'",
        pattern="^(put_away|pick)$",
    )
    worker_id: UUID = Field(..., description="UUID of the worker assigned to the task")
    reference_id: UUID = Field(
        ..., description="UUID of the put_away_list or pick_list"
    )


class TaskFilters(BaseModel):
    """Query parameters for filtering worker tasks.

    Requirements: 16.6
    """

    worker_id: UUID = Field(..., description="Worker UUID to list tasks for")
    status: str | None = Field(
        None,
        description="Filter by status: assigned, in_progress, completed, cancelled",
    )
    date_from: datetime | None = Field(
        None, description="Filter tasks assigned from this date (inclusive)"
    )
    date_to: datetime | None = Field(
        None, description="Filter tasks assigned up to this date (inclusive)"
    )
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


# ===========================================
# RESPONSE SCHEMAS
# ===========================================


class WorkerTaskResponse(BaseModel):
    """Response schema for a worker task.

    Requirements: 16.2
    """

    id: str
    organization_id: str
    task_type: str
    worker_id: str
    reference_id: str
    status: str
    assigned_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class WorkerTaskListResponse(BaseModel):
    """Paginated list response for worker tasks.

    Requirements: 16.6
    """

    tasks: list[WorkerTaskResponse]
    pagination: PaginationMeta
