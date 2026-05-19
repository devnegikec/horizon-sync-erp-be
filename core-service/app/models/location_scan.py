"""Location scan model for QR-based time tracking at bin locations"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class LocationScan(Base):
    """Records start/finish QR scans at bin locations for time tracking."""

    __tablename__ = "location_scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    worker_task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("worker_tasks.id"),
        nullable=False,
        index=True,
    )
    location_code = Column(String(255), nullable=False)
    scan_type = Column(String(10), nullable=False, index=True)
    scanned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    elapsed_seconds = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    worker_task = relationship("WorkerTask", back_populates="location_scans")

    def __repr__(self):
        return (
            f"<LocationScan(id={self.id}, task={self.worker_task_id}, "
            f"location={self.location_code}, type={self.scan_type})>"
        )
