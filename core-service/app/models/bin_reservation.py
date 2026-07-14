"""Bin reservation model for concurrent worker coordination.

A reservation prevents two workers from being directed to the same bin at the
same time. At most one active (un-released) reservation may exist per bin,
enforced by a partial unique index. Time-to-live (TTL) expiry is handled in the
service layer (see BinReservationService).

Design ref: docs/3D_WAREHOUSE_VIEW_DESIGN.md section 4.1
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class BinReservation(Base):
    """Active or historical reservation of a bin location by a worker."""

    __tablename__ = "bin_reservations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    bin_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_locations.id"),
        nullable=False,
        index=True,
    )
    worker_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), nullable=True)
    task_type = Column(String(20), nullable=True)  # 'put_away' or 'pick'

    reserved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    bin_location = relationship("WarehouseLocation")

    def __repr__(self):
        return (
            f"<BinReservation(id={self.id}, bin={self.bin_location_id}, "
            f"worker={self.worker_id}, released={self.released_at is not None})>"
        )
