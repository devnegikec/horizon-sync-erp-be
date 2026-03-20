"""QR Credit Usage model"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer
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
