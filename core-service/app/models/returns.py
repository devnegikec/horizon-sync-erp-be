"""Returns (customer returns) module models.

Implements the R-01 → R-07 backlog in
``docs/Exception Gap/INBOUND_EXCEPTION_AND_RETURNS_GAP_ANALYSIS.md`` and the
contract published in ``RETURNS_WEB_APP_INTEGRATION.md`` /
``RETURNS_HANDHELD_INTEGRATION.md``.

Lifecycle
---------
``return_registrations``  draft → ready → receiving → received → closed (| cancelled)
``return_sessions``       open → ended          (one open session per registration)
``return_receipt_notes``  draft → pending_approval → approved (| rejected)

The handheld owns receiving + condition capture; the web app owns the
registration and the approval/disposition of the draft note. The two never
overlap, mirroring the inbound receiving split.
"""

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

# ---------------------------------------------------------------- vocabularies

#: Registration lifecycle (contract §3.1). ``cancelled`` is terminal.
REGISTRATION_STATUSES = (
    "draft",
    "ready",
    "receiving",
    "received",
    "closed",
    "cancelled",
)

#: Statuses that may still be cancelled — allowed until the first unit is scanned.
CANCELLABLE_REGISTRATION_STATUSES = ("draft", "ready")

#: Statuses the dock may start receiving against.
RECEIVABLE_REGISTRATION_STATUSES = ("ready", "receiving")

#: Return receipt note lifecycle (contract §3.2).
NOTE_STATUSES = ("draft", "pending_approval", "approved", "rejected")

#: Per-unit condition captured on the handheld (contract §3.3).
CONDITIONS = ("good", "damaged", "hold", "quarantine")

#: Per-line final disposition chosen by the supervisor (contract §3.4).
DISPOSITIONS = (
    "release_to_stock",
    "move_to_hold",
    "move_to_quarantine",
    "scrap",
    "return_to_dealer",
)

#: Which conditions each disposition is allowed to be applied to.
DISPOSITION_ALLOWED_CONDITIONS: dict[str, tuple[str, ...]] = {
    "release_to_stock": ("good",),
    "move_to_hold": ("hold", "damaged"),
    "move_to_quarantine": ("quarantine", "damaged"),
    "scrap": ("damaged", "quarantine"),
    "return_to_dealer": ("good", "damaged", "hold", "quarantine"),
}

#: Condition → segregation destination bin, used when the handheld classifies.
CONDITION_DESTINATIONS: dict[str, str] = {
    "damaged": "QUARANTINE",
    "hold": "HOLD",
    "quarantine": "QUARANTINE",
}


class ReturnRegistration(Base):
    """A return declared by the back office against a dispatch reference."""

    __tablename__ = "return_registrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    registration_no = Column(String(100), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="draft", index=True)

    # Reference the return is declared against.
    reference_type = Column(String(30), nullable=False, default="invoice")
    reference_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    reference_no = Column(String(100), nullable=True, index=True)

    party_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    party_name = Column(String(255), nullable=True)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    return_reason_code = Column(String(80), nullable=True)
    return_date = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, nullable=True)

    expected_qty = Column(Numeric(15, 3), nullable=False, default=0)
    received_qty = Column(Numeric(15, 3), nullable=False, default=0)

    cancelled_reason = Column(Text, nullable=True)
    cancelled_by = Column(UUID(as_uuid=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    created_by = Column(UUID(as_uuid=True), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    items = relationship(
        "ReturnRegistrationItem",
        back_populates="registration",
        cascade="all, delete-orphan",
        order_by="ReturnRegistrationItem.sort_order",
    )
    sessions = relationship(
        "ReturnSession",
        back_populates="registration",
        cascade="all, delete-orphan",
        order_by="ReturnSession.started_at",
    )


class ReturnRegistrationItem(Base):
    """One expected line on a return registration (SKU + quantity [+ serials])."""

    __tablename__ = "return_registration_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    registration_id = Column(
        UUID(as_uuid=True),
        ForeignKey("return_registrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="SET NULL"), nullable=True
    )
    sku = Column(String(100), nullable=False, index=True)
    item_name = Column(String(255), nullable=True)
    uom = Column(String(50), nullable=False, default="NOS")
    expected_qty = Column(Numeric(15, 3), nullable=False)
    received_qty = Column(Numeric(15, 3), nullable=False, default=0)
    #: Optional expected serial list; when present the dock validates each scan.
    serials = Column(JSONB, nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    registration = relationship("ReturnRegistration", back_populates="items")


class ReturnSession(Base):
    """A handheld receiving session against one return registration."""

    __tablename__ = "return_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    registration_id = Column(
        UUID(as_uuid=True),
        ForeignKey("return_registrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(String(20), nullable=False, default="open", index=True)
    dock_location = Column(String(120), nullable=True)
    device_id = Column(String(120), nullable=True)
    note = Column(Text, nullable=True)

    expected_qty = Column(Numeric(15, 3), nullable=False, default=0)
    scanned_qty = Column(Numeric(15, 3), nullable=False, default=0)
    classified_qty = Column(Numeric(15, 3), nullable=False, default=0)

    started_by = Column(UUID(as_uuid=True), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    ended_by = Column(UUID(as_uuid=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    registration = relationship("ReturnRegistration", back_populates="sessions")
    items = relationship(
        "ReturnSessionItem",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ReturnSessionItem.scanned_at",
    )


class ReturnSessionItem(Base):
    """A single returned unit captured on the dock, plus its condition."""

    __tablename__ = "return_session_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("return_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    registration_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    registration_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("return_registration_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="SET NULL"), nullable=True
    )

    sku = Column(String(100), nullable=True, index=True)
    qr_identifier = Column(String(255), nullable=False, index=True)
    serial_number = Column(String(255), nullable=True)
    batch_number = Column(String(100), nullable=True)
    quantity = Column(Numeric(15, 3), nullable=False, default=1)
    #: True when the scan exceeded the registered quantity (contract §4.1).
    over_receipt = Column(Boolean, nullable=False, default=False)

    #: ``None`` until the operator classifies the unit.
    condition = Column(String(20), nullable=True, index=True)
    reason_code = Column(String(80), nullable=True)
    note = Column(Text, nullable=True)
    destination = Column(String(30), nullable=True)
    exception_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inbound_exceptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    stock_entered = Column(Boolean, nullable=False, default=False)
    stock_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_locations.id", ondelete="SET NULL"),
        nullable=True,
    )

    device_type = Column(String(50), nullable=True)
    os = Column(String(80), nullable=True)
    scanned_by = Column(UUID(as_uuid=True), nullable=True)
    scanned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    classified_by = Column(UUID(as_uuid=True), nullable=True)
    classified_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    session = relationship("ReturnSession", back_populates="items")


class ReturnReceiptNote(Base):
    """Draft Return Receipt Note produced when a handheld session ends."""

    __tablename__ = "return_receipt_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    note_no = Column(String(100), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="draft", index=True)

    registration_id = Column(
        UUID(as_uuid=True),
        ForeignKey("return_registrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("return_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    expected_qty = Column(Numeric(15, 3), nullable=False, default=0)
    received_qty = Column(Numeric(15, 3), nullable=False, default=0)
    short_qty = Column(Numeric(15, 3), nullable=False, default=0)
    #: Per-condition counters, denormalised for the queue badges.
    good_qty = Column(Numeric(15, 3), nullable=False, default=0)
    damaged_qty = Column(Numeric(15, 3), nullable=False, default=0)
    hold_qty = Column(Numeric(15, 3), nullable=False, default=0)
    quarantine_qty = Column(Numeric(15, 3), nullable=False, default=0)

    note = Column(Text, nullable=True)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by = Column(UUID(as_uuid=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    put_away_generated_at = Column(DateTime(timezone=True), nullable=True)

    created_by = Column(UUID(as_uuid=True), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    items = relationship(
        "ReturnReceiptNoteItem",
        back_populates="note_rel",
        cascade="all, delete-orphan",
        order_by="ReturnReceiptNoteItem.sort_order",
    )
    events = relationship(
        "ReturnReceiptNoteEvent",
        back_populates="note",
        cascade="all, delete-orphan",
    )


class ReturnReceiptNoteItem(Base):
    """One received line on a draft note, carrying condition and disposition."""

    __tablename__ = "return_receipt_note_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    note_id = Column(
        UUID(as_uuid=True),
        ForeignKey("return_receipt_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    registration_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("return_registration_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("return_session_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="SET NULL"), nullable=True
    )

    sku = Column(String(100), nullable=True, index=True)
    item_name = Column(String(255), nullable=True)
    uom = Column(String(50), nullable=False, default="NOS")
    serial_number = Column(String(255), nullable=True)
    batch_number = Column(String(100), nullable=True)
    quantity = Column(Numeric(15, 3), nullable=False, default=1)

    condition = Column(String(20), nullable=True, index=True)
    reason_code = Column(String(80), nullable=True)
    note = Column(Text, nullable=True)
    destination = Column(String(30), nullable=True)
    exception_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inbound_exceptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    disposition = Column(String(40), nullable=True, index=True)
    disposition_reason_code = Column(String(80), nullable=True)
    disposition_note = Column(Text, nullable=True)
    disposed_by = Column(UUID(as_uuid=True), nullable=True)
    disposed_at = Column(DateTime(timezone=True), nullable=True)

    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    note_rel = relationship("ReturnReceiptNote", back_populates="items")


class ReturnReceiptNoteEvent(Base):
    """Append-only audit trail for a return receipt note (X-03)."""

    __tablename__ = "return_receipt_note_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_id = Column(
        UUID(as_uuid=True),
        ForeignKey("return_receipt_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(60), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    details = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

    note = relationship("ReturnReceiptNote", back_populates="events")
