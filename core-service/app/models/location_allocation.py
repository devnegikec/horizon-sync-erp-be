"""Location allocation model for linking locations to item groups"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class LocationAllocation(Base):
    """Links locations to item groups for put-away prioritization (exclusive/preferred)."""

    __tablename__ = "location_allocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_locations.id"),
        nullable=False,
        index=True,
    )
    item_group_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    priority = Column(Integer, default=0)
    allocation_type = Column(String(20), nullable=False, default="preferred")
    is_active = Column(Boolean, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    location = relationship("WarehouseLocation", back_populates="allocations")

    def __repr__(self):
        return (
            f"<LocationAllocation(id={self.id}, location={self.location_id}, "
            f"item_group={self.item_group_id}, type={self.allocation_type})>"
        )
