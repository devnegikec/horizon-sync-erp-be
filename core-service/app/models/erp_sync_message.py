"""ERP sync outbound message queue model (PR-13 / T-13, WF-022, ALT-009).

``ErpSyncMessage`` is an outbound message queued for delivery to the ERP
(SAP). Each row tracks its retry budget, last error and next attempt time so
the queue can be replayed after transient integration failures. The actual
transport is a pluggable hook (see ``ErpSyncService``); a failure alert is
raised once retries are exhausted (ALT-009).
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base
from app.models.types import JSONB, UUID


class ErpSyncStatus(str, enum.Enum):
    """Lifecycle of an outbound ERP sync message."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class ErpSyncMessage(Base):
    """An outbound status-update message queued for the ERP (SAP)."""

    __tablename__ = "erp_sync_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # What is being synced (e.g. entity_type="pick_list", operation="status_update").
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    operation = Column(String(50), nullable=False)

    status = Column(
        String(20),
        nullable=False,
        default=ErpSyncStatus.PENDING.value,
        index=True,
    )

    # Optional link back to the source workflow entities (no FK — reference only).
    pick_list_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    dispatch_record_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    payload = Column(JSONB, nullable=True)

    # Retry budget.
    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    last_error = Column(Text, nullable=True)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)

    # Who triggered the sync (used as the failure-alert recipient).
    created_by = Column(UUID(as_uuid=True), nullable=True)

    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<ErpSyncMessage(id={self.id}, operation='{self.operation}', "
            f"status='{self.status}', attempts={self.attempt_count}/{self.max_attempts})>"
        )
