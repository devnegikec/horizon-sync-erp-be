"""Gate verification session and item models for outbound gate workflow"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class GateVerificationSession(Base):
    """Security gate session linked to a completed pick list for outbound verification."""

    __tablename__ = "gate_verification_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    pick_list_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pick_lists.id"),
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id"),
        nullable=False,
    )
    worker_id = Column(UUID(as_uuid=True), nullable=False)
    vehicle_number = Column(String(100), nullable=True)
    driver_name = Column(String(255), nullable=True)
    driver_contact = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="open")
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    pick_list = relationship("PickList")
    warehouse = relationship("Warehouse")
    items = relationship(
        "GateVerificationItem",
        back_populates="gate_session",
        cascade="all, delete-orphan",
    )
    dispatch_records = relationship("DispatchRecord", back_populates="gate_session")

    def __repr__(self):
        return (
            f"<GateVerificationSession(id={self.id}, pick_list={self.pick_list_id}, "
            f"status={self.status})>"
        )


class GateVerificationItem(Base):
    """Individual QR scans at the gate (verified or unauthorized)."""

    __tablename__ = "gate_verification_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    gate_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("gate_verification_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    qr_identifier = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="verified")
    scanned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Constraints
    __table_args__ = (
        UniqueConstraint("gate_session_id", "qr_identifier", name="uq_gate_session_qr"),
    )

    # Relationships
    gate_session = relationship("GateVerificationSession", back_populates="items")

    def __repr__(self):
        return (
            f"<GateVerificationItem(id={self.id}, sku={self.sku}, "
            f"status={self.status})>"
        )
