"""QR CTA Config model — configurable Call-to-Action buttons for QR landing pages."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base
from app.models.types import UUID


class QRCTAConfig(Base):
    """Per-product CTA button configuration.

    Organizations configure which CTA buttons appear on their QR
    landing pages: "Verify Authenticity", "Visit Website", "Call Support",
    "View Product Details", etc.
    """

    __tablename__ = "qr_cta_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("qr_products.id", ondelete="CASCADE"),
        nullable=True,
    )
    cta_type = Column(String(50), nullable=False)
    cta_label = Column(String(100), nullable=False)
    cta_target = Column(Text, nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self):
        return (
            f"<QRCTAConfig(id={self.id}, type='{self.cta_type}', "
            f"label='{self.cta_label}')>"
        )
