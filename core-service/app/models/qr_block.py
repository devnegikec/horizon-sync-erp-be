"""QR Block model (maps from old Order/qr_blocks)"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class QRBlock(Base):
    """QR Block — a batch of QR codes generated for a product"""

    __tablename__ = "qr_blocks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    product_id = Column(
        UUID(as_uuid=True), ForeignKey("qr_products.id"), nullable=False, index=True
    )

    batch = Column(String(50), nullable=False)
    serial_prefix = Column(String(20), nullable=True)
    sr_number = Column(String(256), nullable=True)
    sr_number_type = Column(String(256), nullable=True)
    quantity = Column(Integer, nullable=False)
    cert_type = Column(String(1), nullable=True)
    size = Column(String(4), nullable=True)
    colour_desc = Column(String(50), nullable=True)
    price = Column(Integer, nullable=True)
    style = Column(String(20), nullable=True)
    task_status = Column(String(20), nullable=True)
    status = Column(String(20), nullable=True)
    task_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    progress_current = Column(Integer, nullable=True)
    progress_total = Column(Integer, nullable=True)
    qr_image = Column(Boolean, default=False)
    manufacture_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    gcs_url = Column(Text, nullable=True)
    download_url = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

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
    product = relationship("QRProduct", back_populates="qr_blocks")
    product_items = relationship("ProductItem", back_populates="block")
    credit_usage = relationship("QRCreditUsage", back_populates="block")

    @property
    def progress_percent(self) -> int | None:
        """Calculate progress percentage"""
        if self.progress_total and self.progress_current:
            return int((self.progress_current / self.progress_total) * 100)
        return None

    def __repr__(self):
        return f"<QRBlock(id={self.id}, batch='{self.batch}', qty={self.quantity}, task_status={self.task_status})>"
