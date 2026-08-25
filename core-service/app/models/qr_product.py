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
    # Shared catalog core link (1:1 from products)
    product_id = Column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    shelf_life_setting_id = Column(
        UUID(as_uuid=True),
        ForeignKey("qr_product_settings.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    serial_prefix_setting_id = Column(
        UUID(as_uuid=True),
        ForeignKey("qr_product_settings.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    name = Column(String(100), nullable=False)
    sku = Column(String(100), nullable=True)
    generic_name = Column(String(100), nullable=True)
     # DEPRECATED — kept nullable for backward compatibility during migration.
    # GTIN now lives on ProductSKU (each variant has its own barcode).
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
    product = relationship("Product", foreign_keys=[product_id])
    landing_page_config = relationship(
        "LandingPageConfig",
        back_populates="product",
        uselist=False,
        cascade="all, delete-orphan",
    )
    shelf_life_setting = relationship(
        "QRProductSetting", foreign_keys=[shelf_life_setting_id]
    )
    serial_prefix_setting = relationship(
        "QRProductSetting", foreign_keys=[serial_prefix_setting_id]
    )

    @property
    def serial_prefix(self) -> str | None:
        """Return the prefix value used when generating block serials."""
        return (
            self.serial_prefix_setting.value
            if self.serial_prefix_setting is not None
            else None
        )

    # Convenience back-references — reachable via product → skus → qr_blocks/product_items
    # Kept for backward compatibility with existing queries during migration.
    qr_blocks = relationship(
        "QRBlock", back_populates="product", cascade="all, delete-orphan"
    )
    product_items = relationship("ProductItem", back_populates="product")
    items = relationship("Item", back_populates="qr_product")

    # SKUs are the direct children of a Product
    skus = relationship("ProductSKU",back_populates="product",cascade="all, delete-orphan",)


    def __repr__(self):
        return f"<QRProduct(id={self.id}, name='{self.name}')>"
