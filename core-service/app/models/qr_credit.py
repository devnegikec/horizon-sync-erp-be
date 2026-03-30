"""QR Credit models — Usage, Balance, and Ledger"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
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
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    total_credits = Column(Integer, nullable=False, default=0)
    used_credits = Column(Integer, nullable=False, default=0)
    balance_credits = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self):
        return f"<QRCreditBalance(id={self.id}, org={self.organization_id}, balance={self.balance_credits})>"


class QRCreditLedger(Base):
    """Audit log recording every credit deduction event"""

    __tablename__ = "qr_credit_ledger"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    block_id = Column(UUID(as_uuid=True), ForeignKey("qr_blocks.id"), nullable=True)
    quantity_deducted = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    block = relationship("QRBlock")

    def __repr__(self):
        return f"<QRCreditLedger(id={self.id}, deducted={self.quantity_deducted})>"
