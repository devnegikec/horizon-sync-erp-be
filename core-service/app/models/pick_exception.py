"""Pick exception + immutable audit models (PR-03 / T-02 + T-05).

``PickException`` records a reason-coded exception raised during pick
execution (discrepancy, damage, serial issue, …). ``PickExceptionAudit`` is an
append-only, immutable trail of every decision taken against an exception —
capture, approval, rejection, resolution and overrides (WF-023 / NFR-005).

The audit table has no update/delete path in the service layer: rows are only
ever inserted, so the trail cannot be rewritten.
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class PickExceptionSeverity(str, enum.Enum):
    """Severity ladder for pick exceptions (maps to ALT-* severity)."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PickExceptionStatus(str, enum.Enum):
    """Lifecycle of a pick exception.

    - ``open``: captured, awaiting attention.
    - ``approved``: supervisor acknowledged (required for short-pick override).
    - ``rejected``: supervisor declined the exception.
    - ``resolved``: closed with a recorded resolution.
    - ``cancelled``: superseded / no longer relevant.
    """

    OPEN = "open"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class PickExceptionAuditEvent(str, enum.Enum):
    """Append-only event kinds for the immutable audit trail."""

    CAPTURED = "captured"
    RESOLVED = "resolved"
    APPROVED = "approved"
    REJECTED = "rejected"
    OVERRIDE = "override"


# Statuses that represent an "active" exception (block a duplicate capture).
_ACTIVE_STATUSES = {
    PickExceptionStatus.OPEN.value,
    PickExceptionStatus.APPROVED.value,
}


class PickException(Base):
    """A reason-coded exception raised against a single pick list item."""

    __tablename__ = "pick_exceptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    pick_list_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pick_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pick_list_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pick_list_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reason_code = Column(String(80), nullable=False, index=True)
    severity = Column(
        String(20),
        nullable=False,
        default=PickExceptionSeverity.WARNING.value,
        index=True,
    )
    reported_by = Column(UUID(as_uuid=True), nullable=True, index=True)
    status = Column(
        String(30),
        nullable=False,
        default=PickExceptionStatus.OPEN.value,
        index=True,
    )

    # Resolution / approval (populated by the supervisor queue, PR-09).
    resolution = Column(Text, nullable=True)
    approver = Column(UUID(as_uuid=True), nullable=True, index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Optional capture context.
    quantity = Column(Numeric(15, 3), nullable=True)
    note = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    audit_events = relationship(
        "PickExceptionAudit",
        back_populates="exception",
        cascade="all, delete-orphan",
        order_by="PickExceptionAudit.created_at",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<PickException(id={self.id}, reason_code='{self.reason_code}', "
            f"status='{self.status}')>"
        )


class PickExceptionAudit(Base):
    """Append-only, immutable audit trail for pick exception decisions."""

    __tablename__ = "pick_exception_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    exception_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pick_exceptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type = Column(String(40), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    from_state = Column(String(30), nullable=True)
    to_state = Column(String(30), nullable=True)
    details = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

    exception = relationship("PickException", back_populates="audit_events")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<PickExceptionAudit(id={self.id}, event_type='{self.event_type}', "
            f"exception={self.exception_id})>"
        )
