"""Dispatch record model for outbound shipment tracking"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class DispatchRecord(Base):
    """Final dispatch record linking pick list, gate session, and vehicle."""

    __tablename__ = "dispatch_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    dispatch_number = Column(String(100), nullable=False, index=True)
    pick_list_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pick_lists.id"),
        nullable=False,
        index=True,
    )
    gate_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("gate_verification_sessions.id"),
        nullable=False,
        index=True,
    )
    invoice_reference = Column(String(255), nullable=True)
    vehicle_number = Column(String(100), nullable=True)
    driver_name = Column(String(255), nullable=True)
    dispatched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    pick_list = relationship("PickList", foreign_keys=[pick_list_id])
    gate_session = relationship(
        "GateVerificationSession", back_populates="dispatch_records"
    )

    def __repr__(self):
        return (
            f"<DispatchRecord(id={self.id}, dispatch_number={self.dispatch_number}, "
            f"pick_list={self.pick_list_id})>"
        )
