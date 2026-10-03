"""Durable request records for QSeal activation retries."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, String, UniqueConstraint

from app.database import Base
from app.models.types import JSONB, UUID


class QSealActivationRequest(Base):
    """One committed activation response per tenant and idempotency key."""

    __tablename__ = "qseal_activation_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # The tenant-scoped unique constraint below is also the lookup index for
    # retries, so a separate organization-only index is unnecessary.
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    idempotency_key = Column(String(100), nullable=False)
    request_hash = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="processing")
    response_payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_qseal_activation_request_org_key",
        ),
        Index("ix_qseal_activation_requests_product_id", "product_id"),
    )
