"""Bulk put-away background job model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base
from app.models.types import JSONB, UUID


class BulkPutAwayJobStatus:
    """Statuses for a bulk put-away background job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BulkPutAwayJob(Base):
    """Tracks an async bulk put-away request and its per-item result."""

    __tablename__ = "bulk_put_away_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    put_away_list_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    job_type = Column(String(20), nullable=False)  # "items" | "qr"
    status = Column(
        String(20),
        nullable=False,
        default=BulkPutAwayJobStatus.QUEUED,
        index=True,
    )
    request_data = Column(JSONB, nullable=True)
    total_items = Column(Integer, nullable=False, default=0)
    completed_items = Column(Integer, nullable=False, default=0)
    failed_items = Column(Integer, nullable=False, default=0)
    result = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return (
            f"<BulkPutAwayJob(id={self.id}, type={self.job_type}, "
            f"status={self.status})>"
        )
