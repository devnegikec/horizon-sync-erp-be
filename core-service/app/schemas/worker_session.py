"""Pydantic schemas for worker login sessions (PR-14 / T-14, WF-009)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class WorkerSessionLoginRequest(BaseModel):
    """Request to start a worker login session."""

    worker_id: UUID = Field(..., description="Worker UUID starting a session")


class WorkerSessionResponse(BaseModel):
    """A worker login session (idle-timeout tracking)."""

    id: str
    organization_id: str
    worker_id: str
    status: str
    last_active_at: str | None = None
    ended_at: str | None = None
    created_at: str | None = None
    timeout_minutes: int
