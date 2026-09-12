"""Pick idempotency key model (PR-04 / T-04, NFR-003 + EX-017).

Stores the outcome of each idempotent pick mutation — ``scan``, ``complete``
and ``cancel`` — keyed by an idempotency key. A replay of the same
(organization, operation, key) returns the stored response instead of
re-executing the mutation, so a rapid double-tap or client retry can never
double-decrement stock or double-post a movement.

Keys are either client-supplied (``Idempotency-Key`` header) or derived
server-side from the task + request payload when the caller omits one.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, String, UniqueConstraint

from app.database import Base
from app.models.types import JSONB, UUID


class PickIdempotencyKey(Base):
    """One recorded, completed idempotent pick mutation."""

    __tablename__ = "pick_idempotency_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    operation = Column(String(50), nullable=False)  # scan | complete | cancel
    idempotency_key = Column(String(255), nullable=False)
    pick_list_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # SHA-256 of the canonical request payload (scan qr_data), for audit/debug.
    request_hash = Column(String(64), nullable=True)
    # JSON snapshot of the successful response, returned verbatim on replay.
    response_json = Column(JSONB, nullable=True)
    status = Column(String(20), nullable=False, default="completed")

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "operation",
            "idempotency_key",
            name="uq_pick_idempotency_org_op_key",
        ),
        Index("ix_pick_idempotency_organization_id", "organization_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<PickIdempotencyKey(operation='{self.operation}', "
            f"key='{self.idempotency_key}')>"
        )
