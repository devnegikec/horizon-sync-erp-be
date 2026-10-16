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
    # Typed document references (T3.5) — replace extra_data string joins so
    # scan events can be correlated to their ASN / session / dispatch by key.
    asn_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("asn_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scan_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scan_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dispatch_record_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dispatch_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # QSeal analytics context. These fields are denormalized snapshots so the
    # dashboard can filter/group scan events without reconstructing the QSeal
    # hierarchy after products or batches have changed.
    product_id = Column(
        UUID(as_uuid=True), ForeignKey("qr_products.id"), nullable=True, index=True
    )
    block_id = Column(
        UUID(as_uuid=True), ForeignKey("qr_blocks.id"), nullable=True, index=True
    )
    qseal_track_id = Column(
        UUID(as_uuid=True), ForeignKey("qseal_tracks.id"), nullable=True, index=True
    )
    qseal_parameter_id = Column(
        UUID(as_uuid=True), ForeignKey("qseal_parameters.id"), nullable=True, index=True
    )
    serial_number = Column(String(75), nullable=True, index=True)
    batch = Column(String(50), nullable=True, index=True)
    qseal_type = Column(String(30), nullable=True, index=True)
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

    # ── QSeal suspicious-scan review ────────────────────────────────────
    # These values are calculated when the event is captured. Keeping the
    # score and rule codes on the event makes the dashboard explainable and
    # avoids recalculating historical results after the rules evolve.
    is_suspicious = Column(Boolean, nullable=False, default=False, index=True)
    risk_score = Column(Integer, nullable=False, default=0, index=True)
    suspicious_reasons = Column(JSONB, nullable=False, default=list)
    review_status = Column(String(20), nullable=False, default="not_flagged", index=True)
    flagged_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    product_item = relationship("ProductItem", back_populates="scan_events")

    def __repr__(self):
        return f"<QRScanEvent(id={self.id}, serial='{self.serial_number}')>"
