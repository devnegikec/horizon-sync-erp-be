"""ProductItem model (individual QR-tagged product unit)"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class ProductItem(Base):
    """
    One physical product unit — the leaf of the hierarchy.


    The `sku_id` FK is denormalized directly here (also reachable via
    block.sku_id) so that unit-level queries like "all items for SKU X"
    run without joining through qr_blocks.

    Through `sku_id` every unit knows:
        Child SKU  →  product_item.sku_id          (the specific variant, e.g. 1L Cooker)
        Parent     →  product_item.sku.product_id  (the master QRProduct)

    Full chain:
        QRProduct  →  ProductSKU  →  QRBlock  →  ProductItem  →  Cascade
    """

    __tablename__ = "product_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    # Kept for backward compatibility during migration
    product_id = Column(
        UUID(as_uuid=True), ForeignKey("qr_products.id"), nullable=False, index=True
    )
    block_id = Column(UUID(as_uuid=True), ForeignKey("qr_blocks.id"), nullable=True)
     # NEW — direct reference to the SKU (variant) this unit belongs to
    # nullable=True during migration; tighten to nullable=False once all
    # existing items have been backfilled via their block.sku_id
    sku_id = Column(UUID(as_uuid=True),ForeignKey("product_skus.id"),nullable=True,
        index=True,)

    serial_number = Column(String(75), nullable=False, index=True)
    # ── Dual-code fields ──────────────────────────────────────────────────────
    secrete_code = Column(String(50), nullable=True)
    token_id = Column(Text, nullable=True)
     # ── State flags ───────────────────────────────────────────────────────────
    is_unit = Column(Boolean, default=False)
    is_suspicious = Column(Boolean, default=False)
    is_verify = Column(Boolean, default=False)
    is_auth = Column(Boolean, default=False)
    qr_deactive = Column(Boolean, default=True)
    qr_deactive_unit = Column(Boolean, default=True)
    qr_active = Column(Boolean, default=True)
    # ── Scan tracking ─────────────────────────────────────────────────────────
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

    __table_args__ = (
        Index(
            "uq_product_items_serial_active",
            serial_number,
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    # Relationships
    product = relationship("QRProduct", back_populates="product_items") # kept for compat
    sku         = relationship("ProductSKU", back_populates="product_items")  # NEW
    block = relationship("QRBlock", back_populates="product_items")
    scan_events = relationship("QRScanEvent", back_populates="product_item")


     # ── Convenience properties ────────────────────────────────────────────────

    @property
    def child_sku_id(self):
        """The specific variant (Child SKU) this unit belongs to."""
        return self.sku_id

    @property
    def parent_product_id(self):
        """The master QRProduct (Parent) this unit belongs to."""
        return self.product_id

    @property
    def variant_label(self):
        """
        Human-readable variant name for this unit.
        e.g. "1 Litre", "Extra Large", "1200mm White"
        Returns None if the SKU relationship is not loaded.
        """
        return self.sku.name if self.sku else None

    @property
    def sku_attributes(self) -> dict:
        """
        Returns the full attribute dict for this unit's SKU.
        e.g. {"Capacity": "1 Litre"} or {"Sweep Size": "1200mm", "Color": "White"}
        Returns empty dict if SKU or its attributes are not loaded.
        """
        if not self.sku:
            return {}
        return self.sku.attribute_display

    def __repr__(self):
        return (
            f"<ProductItem(id={self.id}, "
            f"serial='{self.serial_number}', "
            f"sku_id={self.sku_id})>"
        )
