"""QR Credit models — Usage, Balance, and Ledger"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class QRCreditUsage(Base):
    """Tracks QR credit consumption per block against org monthly quota"""

    __tablename__ = "qr_credit_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    block_id = Column(UUID(as_uuid=True), ForeignKey("qr_blocks.id"), nullable=True)
    quantity = Column(Integer, nullable=False)
    used_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    block = relationship("QRBlock", back_populates="credit_usage")

    def __repr__(self):
        return f"<QRCreditUsage(id={self.id}, qty={self.quantity})>"


class QRCreditBalance(Base):
    """Tracks total, used, and remaining QR generation credits per organization"""

    __tablename__ = "qr_credit_balance"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_qr_credit_balance_org"),
        CheckConstraint(
            "reserved_credits >= 0",
            name="ck_qr_credit_balance_reserved_nonnegative",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    total_credits = Column(Integer, nullable=False, default=0)
    used_credits = Column(Integer, nullable=False, default=0)
    reserved_credits = Column(Integer, nullable=False, default=0)
    balance_credits = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self):
        return f"<QRCreditBalance(id={self.id}, org={self.organization_id}, balance={self.balance_credits})>"


class QRCreditReservation(Base):
    """Durable credit hold for an asynchronous QR Block generation job."""

    __tablename__ = "qr_credit_reservations"
    __table_args__ = (
        UniqueConstraint("block_id", name="uq_qr_credit_reservations_block"),
        CheckConstraint("quantity > 0", name="ck_qr_credit_reservations_quantity"),
        CheckConstraint(
            "status IN ('reserved', 'consumed', 'released')",
            name="ck_qr_credit_reservations_status",
        ),
        Index(
            "ix_qr_credit_reservations_org_status",
            "organization_id",
            "status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    block_id = Column(
        UUID(as_uuid=True),
        ForeignKey("qr_blocks.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="reserved")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    block = relationship("QRBlock")


class QRCreditLedger(Base):
    """Immutable audit log for Organization credit additions and consumption."""

    __tablename__ = "qr_credit_ledger"
    __table_args__ = (
        CheckConstraint("amount <> 0", name="ck_qr_credit_ledger_amount_nonzero"),
        Index(
            "uq_qr_credit_ledger_org_reference",
            "organization_id",
            "reference_id",
            unique=True,
            postgresql_where=text("reference_id IS NOT NULL"),
        ),
        Index(
            "uq_qr_credit_ledger_block_consumption",
            "block_id",
            unique=True,
            postgresql_where=text(
                "block_id IS NOT NULL AND transaction_type = 'block_consumption'"
            ),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    block_id = Column(UUID(as_uuid=True), ForeignKey("qr_blocks.id"), nullable=True)
    transaction_type = Column(String(30), nullable=False)
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    block = relationship("QRBlock")

    def __repr__(self):
        return (
            f"<QRCreditLedger(id={self.id}, type={self.transaction_type}, "
            f"amount={self.amount})>"
        )
