"""Item model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import ItemStatus, ItemType, ValuationMethod
from app.models.types import JSONB


class Item(Base):
    """Item model for inventory management"""

    __tablename__ = "items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Basic Information
    item_code = Column(String(100), nullable=False, index=True)
    item_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    item_group_id = Column(
        UUID(as_uuid=True), ForeignKey("item_groups.id"), nullable=True
    )
    item_type = Column(
        Enum(
            ItemType,
            name="itemtype",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=ItemType.STOCK,
    )

    # Unit of Measure
    uom = Column(String(50), default="Nos")

    # Stock Settings
    maintain_stock = Column(Boolean, default=True)
    valuation_method = Column(
        Enum(
            ValuationMethod,
            name="valuationmethod",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=ValuationMethod.FIFO,
    )
    allow_negative_stock = Column(Boolean, default=False)

    # Variants
    has_variants = Column(Boolean, default=False)
    variant_of = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=True)
    variant_attributes = Column(JSONB, nullable=True)

    # Batch and Serial
    has_batch_no = Column(Boolean, default=False)
    has_serial_no = Column(Boolean, default=False)
    batch_number_series = Column(String(100), nullable=True)
    serial_number_series = Column(String(100), nullable=True)

    # Pricing
    standard_rate = Column(Numeric(15, 2), default=0)
    valuation_rate = Column(Numeric(15, 2), default=0)

    # Reorder Settings
    enable_auto_reorder = Column(Boolean, default=False)
    reorder_level = Column(Integer, default=0)
    reorder_qty = Column(Integer, default=0)
    min_order_qty = Column(Integer, default=1)
    max_order_qty = Column(Integer, nullable=True)

    # Weight
    weight_per_unit = Column(Numeric(10, 3), nullable=True)
    weight_uom = Column(String(50), nullable=True)

    # Quality Inspection
    inspection_required_before_purchase = Column(Boolean, default=False)
    inspection_required_before_delivery = Column(Boolean, default=False)
    quality_inspection_template = Column(UUID(as_uuid=True), nullable=True)

    # Additional Info
    barcode = Column(String(100), nullable=True)
    status = Column(
        Enum(
            ItemStatus,
            name="itemstatus",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=ItemStatus.ACTIVE,
    )
    image_url = Column(String(500), nullable=True)
    images = Column(JSONB, nullable=True)
    tags = Column(JSONB, nullable=True)
    custom_fields = Column(JSONB, nullable=True)
    extra_data = Column(JSONB, nullable=True)

    # Audit fields
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
    item_group = relationship("ItemGroup", back_populates="items")
    variant_parent = relationship("Item", remote_side=[id], backref="variants")

    def __repr__(self):
        return f"<Item(id={self.id}, code='{self.item_code}', name='{self.item_name}')>"
