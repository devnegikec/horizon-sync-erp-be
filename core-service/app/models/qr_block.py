"""QR Block model (maps from old Order/qr_blocks)"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class QRBlock(Base):
    """
    A print batch of QR codes created for one specific ProductSKU.

    Previously a Block pointed directly at QRProduct.  It now points at
    ProductSKU so every batch knows exactly which variant was printed.

    Full chain:
        QRProduct  →  ProductSKU  →  QRBlock  →  ProductItem

    Migration notes:
        - `sku_id`     — new FK, nullable=True during migration.
                         Tighten to nullable=False once all existing blocks
                         have been backfilled with a default SKU.
        - `product_id` — kept for backward compatibility; derivable via
                         sku.product_id once migration is complete.
        - `size`, `colour_desc`, `price`, `style` — variant-specific fields
                         that now live on ProductSKU.  Kept nullable here so
                         existing rows are not broken.  Remove after migration.
    """

    __tablename__ = "qr_blocks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
     # ── Parents ───────────────────────────────────────────────────────────────
    # Primary parent — the specific variant being printed
    sku_id = Column(UUID(as_uuid=True),ForeignKey("product_skus.id"),
        nullable=True,   # → nullable=False after migration
        index=True,)

    # Kept for backward compatibility during migration
    product_id = Column(
        UUID(as_uuid=True), ForeignKey("qr_products.id"), nullable=False, index=True
    )
    channel_setting_id = Column(
        UUID(as_uuid=True),
        ForeignKey("qr_product_settings.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    destination_setting_id = Column(
        UUID(as_uuid=True),
        ForeignKey("qr_product_settings.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # ── Batch identity ────────────────────────────────────────────────────────
    batch = Column(String(50), nullable=False)
    qr_type = Column(String(30), nullable=False, default="dynamic")
    serial_prefix = Column(String(20), nullable=True)
    starting_serial = Column(String(10), nullable=True)
    sr_number = Column(String(256), nullable=True)
    sr_number_type = Column(String(256), nullable=True)
    quantity = Column(Integer, nullable=False)
    cert_type = Column(String(1), nullable=True)
     # ── DEPRECATED variant fields ─────────────────────────────────────────────
    # These are now stored on ProductSKU / VariantAttributeValue.
    # Kept nullable so existing rows remain valid.  Remove after migration
    size = Column(String(4), nullable=True)
    colour_desc = Column(String(50), nullable=True)
    price = Column(Integer, nullable=True)
    style = Column(String(20), nullable=True)

    # ── Task / generation state ───────────────────────────────────────────────
    task_status = Column(String(20), nullable=True)
    status = Column(String(20), nullable=True)
    task_id = Column(String(255), nullable=True)
    qr_image = Column(Boolean, default=False)
    generated_count = Column(Integer, nullable=False, default=0)
    progress = Column(Integer, nullable=False, default=0)
    error_code = Column(String(50), nullable=True)
    error_message = Column(String(500), nullable=True)
    # ── Dates ────────────────────────────────────────────────────────────────
    manufacture_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    # ── Master packs ─────────────────────────────────────────────────────────
    master_pack_enabled = Column(Boolean, default=False)
    master_pack_size = Column(Integer, nullable=True)

    # ── Storage ──────────────────────────────────────────────────────────────
    gcs_url = Column(Text, nullable=True)
    download_url = Column(Text, nullable=True)
    artifact_object_key = Column(Text, nullable=True)
    artifact_size_bytes = Column(BigInteger, nullable=True)
    artifact_checksum_sha256 = Column(String(64), nullable=True)
    artifact_generated_at = Column(DateTime(timezone=True), nullable=True)
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

    __table_args__ = (
        CheckConstraint(
            "qr_type IN "
            "('dynamic', 'static', 'dual', 'secure_code', 'one_time', "
            "'post_activation')",
            name="ck_qr_blocks_qr_type",
        ),
        CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="ck_qr_blocks_progress",
        ),
        Index(
            "uq_qr_blocks_org_batch_active",
            organization_id,
            func.lower(batch),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    # Relationships
    product = relationship("QRProduct", back_populates="qr_blocks")
    product_items = relationship("ProductItem", back_populates="block")
    credit_usage = relationship("QRCreditUsage", back_populates="block")
    sku     = relationship("ProductSKU", back_populates="qr_blocks")
    channel_setting = relationship(
        "QRProductSetting", foreign_keys=[channel_setting_id]
    )
    destination_setting = relationship(
        "QRProductSetting", foreign_keys=[destination_setting_id]
    )

    @property
    def distribution_channel(self) -> str | None:
        return self.channel_setting.label if self.channel_setting else None

    @property
    def destination_market(self) -> str | None:
        return self.destination_setting.label if self.destination_setting else None

    @property
    def download_available(self) -> bool:
        return bool(
            self.artifact_object_key or self.download_url or self.status == "completed"
        )

    def __repr__(self):
        return f"<QRBlock(id={self.id}, batch='{self.batch}', qty={self.quantity})>"
