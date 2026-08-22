"""
ProductSKU model.

Sits between QRProduct and QRBlock in the hierarchy:

    QRProduct  (master — name, brand, landing page, activation method)
        └── ProductSKU  (variant — e.g. Pressure Cooker 1L)
                └── QRBlock  (print batch — quantity, cert type, serial format)
                        └── ProductItem  (individual unit — serial code + scratch code + QR)

Each SKU links to its variant definition through ProductSKUAttributeValue rows,
which reference VariantAttributeValue records.

Example — Fan SKU "FAN-1200-WHT":
    ProductSKU.sku_attribute_values[0].attribute_value  →  VariantAttributeValue(value="1200mm")
    ProductSKU.sku_attribute_values[1].attribute_value  →  VariantAttributeValue(value="White")
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class ProductSKU(Base):
    """A specific sellable variant of a QRProduct."""

    __tablename__ = "product_skus"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # ── Parent ────────────────────────────────────────────────────────────────
    # SKU's direct parent is always a QRProduct.
    product_id = Column(UUID(as_uuid=True),ForeignKey("qr_products.id"),nullable=False,index=True,)

    # Auto-generated from product + attribute values)
    sku_code = Column(String(100), nullable=False, unique=True, index=True)

    # Human-readable variant label shown in UI / on certs
    # e.g. "1 Litre", "Extra Large", "1200mm White"
    name = Column(String(100), nullable=True)

    # ── Variant-specific fields ───────────────────────────────────────────────
    # These live on SKU, NOT on QRProduct, because they differ per variant.

    gtin = Column(String(20),       nullable=True)  # barcode — unique per variant
    mrp  = Column(Numeric(10, 2),   nullable=True)  # price — can differ per variant

    # Serial number format for QR generation in batches under this SKU.
    # Overrides the product-level sr_number_type when set.
    # R6DAN | R4DAN | S8DN | S10DN
    sr_number_type = Column(String(50), nullable=True)

    # Optional: variant-specific image and warranty
    # (e.g. a 5L cooker may have a different product image than a 1L)
    image_url             = Column(Text,    nullable=True)
    warranty_period_months= Column(Integer, nullable=True)

    is_active  = Column(Boolean, default=True)
    extra_data = Column(JSONB,   nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    # Parent product
    product = relationship("QRProduct", back_populates="skus")

    # Variant attribute values linked to this SKU (via join table)
    # Access the actual attribute value: sku.sku_attribute_values[n].attribute_value
    sku_attribute_values = relationship(
        "ProductSKUAttributeValue",
        back_populates="sku",
        cascade="all, delete-orphan",
    )

    # All print batches created under this SKU
    qr_blocks = relationship(
        "QRBlock",
        back_populates="sku",
        cascade="all, delete-orphan",
    )

    # All individual units that belong to this SKU
    # (denormalized from block.sku_id for fast unit-level queries)
    product_items = relationship("ProductItem", back_populates="sku")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def attribute_display(self) -> dict:
        """
        Returns a dict of attribute name → display value for this SKU.

        Example output:
            {"Capacity": "1 Litre"}
            {"Sweep Size": "1200mm", "Color": "White"}
        """
        return {
            link.attribute_value.attribute.name: link.attribute_value.label
            for link in self.sku_attribute_values
        }

    def __repr__(self):
        return (f"<ProductSKU(id={self.id}, "f"sku_code='{self.sku_code}', "
            f"product_id={self.product_id})>"
        )
