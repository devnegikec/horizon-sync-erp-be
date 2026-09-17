"""Queryable ASN shortage balances produced by approved receiving receipts."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, UniqueConstraint

from app.database import Base
from app.models.types import UUID


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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "asn_order_item_id",
            name="uq_inbound_short_balance_asn_item",
        ),
    )
