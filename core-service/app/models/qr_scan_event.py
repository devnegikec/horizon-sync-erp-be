"""QR Scan Event model — replaces external Metamo integration"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class QRScanEvent(Base):
    """Records every QR code scan with device and geo data"""

    __tablename__ = "qr_scan_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    product_item_id = Column(
        UUID(as_uuid=True), ForeignKey("product_items.id"), nullable=True
    )
    serial_number = Column(String(75), nullable=True, index=True)
    scan_timestamp = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    device_type = Column(String(50), nullable=True)
    os = Column(String(50), nullable=True)
    browser = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    street_address = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)

    # Public verification analytics. ``event_id`` is supplied by the landing
    # page and makes retries/refreshes idempotent.
    event_id = Column(UUID(as_uuid=True), nullable=True, unique=True, index=True)
    verification_status = Column(String(40), nullable=True, index=True)
    authentic = Column(Boolean, nullable=True)
    qr_channel = Column(String(10), nullable=True)
    ip_hash = Column(String(64), nullable=True)
    is_bot = Column(Boolean, nullable=False, default=False)
    location_source = Column(String(20), nullable=True)
    location_accuracy_meters = Column(Integer, nullable=True)

    # ── Phase 1 enhancements ────────────────────────────────────────────
    user_agent_raw = Column(Text, nullable=True)
    user_agent_parsed = Column(JSONB, nullable=True)
    qr_type = Column(String(30), nullable=True)
    cta_action = Column(String(50), nullable=True)
    referrer_url = Column(Text, nullable=True)
    language = Column(String(10), nullable=True)

    # Relationships
    product_item = relationship("ProductItem", back_populates="scan_events")

    def __repr__(self):
        return f"<QRScanEvent(id={self.id}, serial='{self.serial_number}')>"
