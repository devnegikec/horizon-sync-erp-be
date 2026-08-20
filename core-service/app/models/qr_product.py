"""QR Product model"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
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
    sku = Column(String(100), nullable=True)
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

    # ── Synced from Item ──
    # TODO(DEPRECATION): These columns are duplicated from Item for sync.
    # No action needed when QRProduct is removed — they disappear with the table.
    item_code = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    uom = Column(String(50), nullable=True)
    standard_rate = Column(Numeric(15, 2), nullable=True)
    valuation_rate = Column(Numeric(15, 2), nullable=True)
    weight_per_unit = Column(Numeric(10, 3), nullable=True)
    weight_uom = Column(String(50), nullable=True)
    barcode = Column(String(100), nullable=True)
    maintain_stock = Column(Boolean, nullable=True)
    has_batch_no = Column(Boolean, nullable=True)
    has_serial_no = Column(Boolean, nullable=True)
    item_type = Column(String(50), nullable=True)
    valuation_method = Column(String(50), nullable=True)
    allow_negative_stock = Column(Boolean, nullable=True)
    item_group_id = Column(UUID(as_uuid=True), nullable=True)
    has_variants = Column(Boolean, nullable=True)
    variant_of = Column(UUID(as_uuid=True), nullable=True)
    variant_attributes = Column(JSONB, nullable=True)
    batch_number_series = Column(String(100), nullable=True)
    serial_number_series = Column(String(100), nullable=True)
    enable_auto_reorder = Column(Boolean, nullable=True)
    reorder_level = Column(Integer, nullable=True)
    reorder_qty = Column(Integer, nullable=True)
    min_order_qty = Column(Integer, nullable=True)
    max_order_qty = Column(Integer, nullable=True)
    inspection_required_before_purchase = Column(Boolean, nullable=True)
    inspection_required_before_delivery = Column(Boolean, nullable=True)
    quality_inspection_template = Column(UUID(as_uuid=True), nullable=True)
    sales_tax_template_id = Column(UUID(as_uuid=True), nullable=True)
    purchase_tax_template_id = Column(UUID(as_uuid=True), nullable=True)
    images = Column(JSONB, nullable=True)
    tags = Column(JSONB, nullable=True)
    custom_fields = Column(JSONB, nullable=True)

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
    landing_page_config = relationship(
        "LandingPageConfig",
        back_populates="product",
        uselist=False,
        cascade="all, delete-orphan",
    )
    qr_blocks = relationship(
        "QRBlock", back_populates="product", cascade="all, delete-orphan"
    )
    product_items = relationship("ProductItem", back_populates="product")
    items = relationship("Item", back_populates="qr_product")

    def __repr__(self):
        return f"<QRProduct(id={self.id}, name='{self.name}')>"
