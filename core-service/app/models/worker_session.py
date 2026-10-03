"""Worker login session model (PR-14 / T-14, WF-009).

``WorkerSession`` tracks an active handheld login session for a warehouse
worker so idle timeout (``pick.session_timeout_minutes``) can be enforced
server-side. Lockout state (failed attempts / locked-until) lives on the
``WMSWorker`` itself.
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String

from app.database import Base
from app.models.types import UUID


class WorkerSessionStatus(str, enum.Enum):
    """Lifecycle of a worker login session."""

    ACTIVE = "active"
    EXPIRED = "expired"
    ENDED = "ended"


class WorkerSession(Base):
    """A worker handheld login session (idle-timeout enforcement)."""

    __tablename__ = "worker_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    worker_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    status = Column(
        String(20),
        nullable=False,
        default=WorkerSessionStatus.ACTIVE.value,
        index=True,
    )

    # Idle tracking: refreshed on each touch; expiry = now - timeout_minutes.
    last_active_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<WorkerSession(id={self.id}, worker={self.worker_id}, "
            f"status='{self.status}')>"
        )
