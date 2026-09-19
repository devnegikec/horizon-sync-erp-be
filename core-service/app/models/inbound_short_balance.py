"""Queryable ASN shortage balances produced by approved receiving receipts.

A balance tracks the expected vs received quantity of one ASN line. It stays
``open`` while a residual short exists, flips to ``resolved`` when later
receipts bring ``received_qty`` up to ``expected_qty``, or is closed as
``written_off`` by an authorized manager (reason-coded, audited).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID

#: ``open`` — residual short exists; ``resolved`` — fully received;
#: ``written_off`` — manager-approved formal closure of the residual short.
BALANCE_STATUS_OPEN = "open"
BALANCE_STATUS_RESOLVED = "resolved"
BALANCE_STATUS_WRITTEN_OFF = "written_off"
BALANCE_STATUSES = (
    BALANCE_STATUS_OPEN,
    BALANCE_STATUS_RESOLVED,
    BALANCE_STATUS_WRITTEN_OFF,
)


class InboundShortBalance(Base):
    """Current short balance for an ASN line, linked to its latest receipt note."""

    __tablename__ = "inbound_short_balances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    asn_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("asn_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asn_order_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("asn_order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receiving_slip_id = Column(
        UUID(as_uuid=True),
        ForeignKey("receiving_slips.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="SET NULL"), nullable=True
    )
    sku = Column(String(100), nullable=False)
    expected_qty = Column(Numeric(15, 3), nullable=False)
    received_qty = Column(Numeric(15, 3), nullable=False)
    short_qty = Column(Numeric(15, 3), nullable=False)
    status = Column(String(20), nullable=False, default="open", index=True)
    # Dock-side reason code carried over from the flagged receipt line.
    reason_code = Column(String(80), nullable=True)
    note = Column(Text, nullable=True)
    # Formal closure of a residual shortage (manager approved).
    close_reason_code = Column(String(80), nullable=True)
    close_note = Column(Text, nullable=True)
    closed_by = Column(UUID(as_uuid=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    events = relationship(
        "InboundShortBalanceEvent",
        back_populates="balance",
        cascade="all, delete-orphan",
        order_by="InboundShortBalanceEvent.created_at",
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "asn_order_item_id",
            name="uq_inbound_short_balance_asn_item",
        ),
    )


class InboundShortBalanceEvent(Base):
    """Append-only history of a short balance (arrival-level traceability)."""

    __tablename__ = "inbound_short_balance_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    balance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inbound_short_balances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receiving_slip_id = Column(
        UUID(as_uuid=True),
        ForeignKey("receiving_slips.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    #: ``created`` | ``updated`` | ``resolved`` | ``written_off``
    event_type = Column(String(30), nullable=False, index=True)
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=False)
    expected_qty = Column(Numeric(15, 3), nullable=False)
    received_qty = Column(Numeric(15, 3), nullable=False)
    short_qty = Column(Numeric(15, 3), nullable=False)
    reason_code = Column(String(80), nullable=True)
    note = Column(Text, nullable=True)
    actor_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    balance = relationship("InboundShortBalance", back_populates="events")

    def __repr__(self) -> str:
        return (
            f"<InboundShortBalanceEvent(id={self.id}, balance={self.balance_id}, "
            f"type={self.event_type}, short_qty={self.short_qty})>"
        )
