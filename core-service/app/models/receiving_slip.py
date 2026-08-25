"""Receiving slip and receiving slip item models for inbound workflow"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class ReceivingSlip(Base):
    """Formal record of goods received, generated from closed scan sessions."""

    __tablename__ = "receiving_slips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    slip_number = Column(String(100), nullable=False)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scan_sessions.id"),
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id"),
        nullable=False,
        index=True,
    )
    asn_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("asn_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vehicle_arrival_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_arrivals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(30), nullable=False, default="pending_review")
    total_boxes = Column(Integer, default=0)
    total_items = Column(Integer, default=0)
    rejection_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    session = relationship("ScanSession", back_populates="receiving_slips")
    warehouse = relationship("Warehouse")
    asn_order = relationship("AsnOrder", foreign_keys=[asn_order_id])
    vehicle_arrival = relationship("VehicleArrival", back_populates="receiving_slips")
    items = relationship(
        "ReceivingSlipItem", back_populates="slip", cascade="all, delete-orphan"
    )
    put_away_lists = relationship("PutAwayList", back_populates="receiving_slip")

    def __repr__(self):
        return (
            f"<ReceivingSlip(id={self.id}, slip_number={self.slip_number}, "
            f"status={self.status})>"
        )


class ReceivingSlipItem(Base):
    """Individual line items on a receiving slip, grouped by SKU and batch."""

    __tablename__ = "receiving_slip_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    slip_id = Column(
        UUID(as_uuid=True),
        ForeignKey("receiving_slips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku = Column(String(100), nullable=False, index=True)
    batch_number = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    box_count = Column(Integer, default=0)
    flag = Column(String(20), default="ok")
    notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    rejected_by = Column(UUID(as_uuid=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)

    # Put-away tracking (two-step inbound: receive → assign bin)
    bin_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_locations.id"),
        nullable=True,
        index=True,
    )
    put_away_status = Column(String(20), default="pending")
    put_away_at = Column(DateTime(timezone=True), nullable=True)
    put_away_by = Column(UUID(as_uuid=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    slip = relationship("ReceivingSlip", back_populates="items")
    bin_location = relationship("WarehouseLocation")

    def __repr__(self):
        return (
            f"<ReceivingSlipItem(id={self.id}, sku={self.sku}, "
            f"qty={self.quantity}, flag={self.flag})>"
        )
