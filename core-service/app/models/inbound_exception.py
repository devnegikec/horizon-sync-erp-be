"""Inbound exception, disposition, evidence, and audit models.

Exceptions are deliberately independent from receiving-slip lines: an unknown
identity must be recorded even though it never becomes a receivable line item.
"""

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


class InboundExceptionReason(Base):
    """Structured, tenant-configurable inbound exception reason code."""

    __tablename__ = "inbound_exception_reasons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    code = Column(String(80), nullable=False, unique=True, index=True)
    name = Column(String(160), nullable=False)
    category = Column(String(40), nullable=False)
    default_destination = Column(String(30), nullable=True)
    requires_approval = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class InboundException(Base):
    """A reason-coded inbound exception and its controlled disposition."""

    __tablename__ = "inbound_exceptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asn_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("asn_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scan_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    slip_id = Column(
        UUID(as_uuid=True),
        ForeignKey("receiving_slips.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    slip_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("receiving_slip_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scan_session_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scan_session_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tracking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scanned_item_tracking.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    exception_type = Column(String(50), nullable=False, index=True)
    reason_code = Column(String(80), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="open", index=True)
    condition_code = Column(String(30), nullable=False, default="GOOD")
    destination = Column(String(30), nullable=True, index=True)
    destination_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    qr_identifier = Column(String(255), nullable=True, index=True)
    sku = Column(String(100), nullable=True, index=True)
    batch_number = Column(String(100), nullable=True)
    quantity = Column(Integer, nullable=False, default=0)
    note = Column(Text, nullable=True)
    raw_qr_data = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)

    created_by = Column(UUID(as_uuid=True), nullable=True, index=True)
    approved_by = Column(UUID(as_uuid=True), nullable=True, index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    disposition = Column(String(40), nullable=True)
    disposition_note = Column(Text, nullable=True)
    disposed_by = Column(UUID(as_uuid=True), nullable=True, index=True)
    disposed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    evidence = relationship(
        "InboundExceptionEvidence",
        back_populates="exception",
        cascade="all, delete-orphan",
    )
    events = relationship(
        "InboundExceptionEvent",
        back_populates="exception",
        cascade="all, delete-orphan",
    )


class InboundExceptionEvidence(Base):
    """Optional file evidence uploaded against an inbound exception."""

    __tablename__ = "inbound_exception_evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exception_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inbound_exceptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    storage_key = Column(String(500), nullable=False, unique=True)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(120), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    exception = relationship("InboundException", back_populates="evidence")


class InboundExceptionEvent(Base):
    """Append-only execution trail for inbound exception decisions."""

    __tablename__ = "inbound_exception_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exception_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inbound_exceptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(60), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    device_context = Column(JSONB, nullable=True)
    details = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

    exception = relationship("InboundException", back_populates="events")
