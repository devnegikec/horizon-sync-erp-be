"""Pydantic schemas for the ERP sync outbound queue (PR-13 / T-13, WF-022)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import PaginationMeta


class ErpSyncMessageResponse(BaseModel):
    """A single outbound ERP sync queue message."""

    id: str
    organization_id: str
    entity_type: str
    entity_id: str
    operation: str
    status: str
    pick_list_id: str | None = None
    dispatch_record_id: str | None = None
    attempt_count: int
    max_attempts: int
    last_error: str | None = None
    next_attempt_at: datetime | None = None
    sent_at: datetime | None = None
    created_at: datetime | None = None


class ErpSyncListResponse(BaseModel):
    """Paginated list of ERP sync queue messages."""

    messages: list[ErpSyncMessageResponse]
    pagination: PaginationMeta


class ErpSyncFlushResponse(BaseModel):
    """Summary of a flush attempt over the due pending queue."""

    processed: int
    sent: int
    retried: int
    failed: int
