"""Scanned Item Tracking — dual-axis state machine for receiving & put-away."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class ScannedItemTracking(Base):
    """Tracks each scanned item through independent receiving and put-away axes."""

    __tablename__ = "scanned_item_tracking"
    __audited__ = False

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id"),
        nullable=False,
        index=True,
    )

    # ── Scan context ──
    scan_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scan_sessions.id"),
        nullable=True,
        index=True,
    )
    scan_session_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scan_session_items.id"),
        nullable=True,
        unique=True,
    )
    qr_identifier = Column(String(255), nullable=False, index=True)

    # ── Item details (extracted from QR once) ──
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
    )
    sku = Column(String(100), nullable=False)
    batch_number = Column(String(100), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)

    # ── Receiving axis ──
    receiving_status = Column(String(30), nullable=False, default="scanned", index=True)
    receiving_slip_id = Column(
        UUID(as_uuid=True),
        ForeignKey("receiving_slips.id"),
        nullable=True,
    )
    received_at = Column(DateTime(timezone=True), nullable=True)
    received_by = Column(UUID(as_uuid=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # ── Put-away axis ──
    putaway_status = Column(String(30), nullable=False, default="pending", index=True)
    put_away_list_id = Column(
        UUID(as_uuid=True),
        ForeignKey("put_away_lists.id"),
        nullable=True,
    )
    put_away_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("put_away_list_items.id"),
        nullable=True,
    )
    bin_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_locations.id"),
        nullable=True,
    )
    # Current physical location. Unlike bin_location_id (the eventual put-away
    # target), this can be RECEIVING-STAGE, HOLD, or QUARANTINE.
    stock_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    putaway_at = Column(DateTime(timezone=True), nullable=True)
    putaway_by = Column(UUID(as_uuid=True), nullable=True)

    # ── Derived ──
    stock_entered = Column(Boolean, nullable=False, default=False)
    stock_entered_at = Column(DateTime(timezone=True), nullable=True)

    # ── Metadata ──
    scanned_by = Column(UUID(as_uuid=True), nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # ── Relationships ──
    scan_session = relationship("ScanSession", backref="item_trackings")
    warehouse = relationship("Warehouse", backref="item_trackings")
    item = relationship("Item", backref="item_trackings")
    bin_location = relationship("WarehouseLocation", backref="item_trackings")

    def __repr__(self):
        return (
            f"<ScannedItemTracking(qr='{self.qr_identifier}', "
            f"recv='{self.receiving_status}', pa='{self.putaway_status}', "
            f"stock={self.stock_entered})>"
        )
