"""Scan session and scan session item models for QR-based inbound/gate workflows"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class ScanSession(Base):
    """Groups QR scans into inbound or gate sessions."""

    __tablename__ = "scan_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    session_type = Column(String(20), nullable=False)
    worker_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id"),
        nullable=False,
        index=True,
    )
    dock_location = Column(String(255), nullable=True)
    asn_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("asn_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(20), nullable=False, default="open")
    total_boxes_scanned = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    items = relationship(
        "ScanSessionItem", back_populates="session", cascade="all, delete-orphan"
    )
    warehouse = relationship("Warehouse")
    asn_order = relationship("AsnOrder", foreign_keys=[asn_order_id])
    receiving_slips = relationship("ReceivingSlip", back_populates="session")

    def __repr__(self):
        return (
            f"<ScanSession(id={self.id}, type={self.session_type}, "
            f"status={self.status})>"
        )


class ScanSessionItem(Base):
    """Individual QR scans within a session."""

    __tablename__ = "scan_session_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scan_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    qr_identifier = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=False, index=True)
    raw_quantity = Column(Integer, nullable=False)
    batch_number = Column(String(100), nullable=False)
    raw_qr_data = Column(Text, nullable=False)
    scanned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    packaging_unit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("item_packaging_units.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("session_id", "qr_identifier", name="uq_session_qr"),
    )

    # Relationships
    session = relationship("ScanSession", back_populates="items")
    packaging_unit = relationship("ItemPackagingUnit")

    def __repr__(self):
        return (
            f"<ScanSessionItem(id={self.id}, session={self.session_id}, "
            f"sku={self.sku}, raw_qty={self.raw_quantity})>"
        )
