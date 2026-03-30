"""Brand model with ECDSA key pair for QR signing"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class Brand(Base):
    """Brand — holds ECDSA P-256 key pair for digital signing of QR codes"""

    __tablename__ = "brands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    name = Column(String(256), nullable=True)
    short_code = Column(String(256), nullable=True)
    public_key = Column(String(512), nullable=True)
    private_key_encrypted = Column(Text, nullable=True)

    # Audit
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    qr_products = relationship("QRProduct", back_populates="brand")

    def __repr__(self):
        return f"<Brand(id={self.id}, name='{self.name}')>"
