"""Worker task model for tracking put-away and pick tasks assigned to workers"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class WorkerTask(Base):
    """Tracks put-away and pick tasks assigned to warehouse workers."""

    __tablename__ = "worker_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    task_type = Column(String(20), nullable=False, index=True)
    worker_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    reference_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(20), nullable=False, default="assigned", index=True)
    assigned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    location_scans = relationship("LocationScan", back_populates="worker_task")

    def __repr__(self):
        return (
            f"<WorkerTask(id={self.id}, type={self.task_type}, "
            f"worker={self.worker_id}, status={self.status})>"
        )
