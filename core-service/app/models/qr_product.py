"""QR Product model"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class QRProduct(Base):
    """QR Product — maps from old integration_product"""

    __tablename__ = "qr_products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True)

    name = Column(String(100), nullable=False)
    generic_name = Column(String(100), nullable=True)
    gtin = Column(String(20), nullable=True)
    industry = Column(String(100), nullable=True)
    landing_page = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    banner_image_url = Column(Text, nullable=True)
    email = Column(String(255), nullable=True)
    phone_number = Column(String(15), nullable=True)
    client_product_auth_url = Column(Text, nullable=True)
    activation_method = Column(String(4), default="pre")  # pre | post
    sr_number_type = Column(String(50), nullable=True)
    redirect_to_client = Column(Boolean, default=False)
    warranty_period_months = Column(Integer, nullable=True)
    qr_type = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True)
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
    brand = relationship("Brand", back_populates="qr_products")
    qr_blocks = relationship(
        "QRBlock", back_populates="product", cascade="all, delete-orphan"
    )
    product_items = relationship("ProductItem", back_populates="product")
    items = relationship("Item", back_populates="qr_product")

    def __repr__(self):
        return f"<QRProduct(id={self.id}, name='{self.name}')>"
