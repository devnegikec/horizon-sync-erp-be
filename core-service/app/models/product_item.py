"""ProductItem model (individual QR-tagged product unit)"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class ProductItem(Base):
    """Individual product unit with a unique serial number / QR code"""

    __tablename__ = "product_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    product_id = Column(
        UUID(as_uuid=True), ForeignKey("qr_products.id"), nullable=False, index=True
    )
    block_id = Column(UUID(as_uuid=True), ForeignKey("qr_blocks.id"), nullable=True)

    serial_number = Column(String(75), nullable=False, index=True)
    secrete_code = Column(String(50), nullable=True)
    token_id = Column(Text, nullable=True)
    is_unit = Column(Boolean, default=False)
    is_suspicious = Column(Boolean, default=False)
    is_verify = Column(Boolean, default=False)
    is_auth = Column(Boolean, default=False)
    qr_deactive = Column(Boolean, default=True)
    qr_deactive_unit = Column(Boolean, default=True)
    qr_active = Column(Boolean, default=True)
    scan_date = Column(DateTime(timezone=True), nullable=True)
    scans = Column(Integer, default=0)
    scan_count = Column(Integer, default=0)
    last_scanned_at = Column(DateTime(timezone=True), nullable=True)
    destination_market = Column(String(100), nullable=True)
    extra_data = Column(JSONB, nullable=True)

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
    product = relationship("QRProduct", back_populates="product_items")
    block = relationship("QRBlock", back_populates="product_items")
    scan_events = relationship("QRScanEvent", back_populates="product_item")

    def __repr__(self):
        return f"<ProductItem(id={self.id}, serial='{self.serial_number}')>"
