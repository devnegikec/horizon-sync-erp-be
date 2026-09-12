"""ItemPackagingUnit model — defines packaging units per item with physical dimensions"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class ItemPackagingUnit(Base):
    """Defines a packaging unit for an item (e.g., Each, Box of 12, Pallet of 144)."""

    __tablename__ = "item_packaging_units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    packaging_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("packaging_types.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    unit_name = Column(String(100), nullable=False)  # legacy display cache; prefer packaging_type_id
    qr_identifier = Column(String(255), nullable=True, unique=True)
    conversion_factor = Column(Numeric(15, 6), nullable=False)
    items_per_master_pack = Column(Integer, nullable=True)
    length_mm = Column(Numeric(10, 2), nullable=True)
    width_mm = Column(Numeric(10, 2), nullable=True)
    height_mm = Column(Numeric(10, 2), nullable=True)
    weight_grams = Column(Numeric(10, 2), nullable=True)
    is_base_unit = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint("item_id", "unit_name", name="uq_item_unit_name"),
        CheckConstraint("conversion_factor > 0", name="chk_conversion_factor_positive"),
    )

    # Relationships
    item = relationship("Item", back_populates="packaging_units")
    packaging_type = relationship("PackagingType")

    def __repr__(self):
        return (
            f"<ItemPackagingUnit(id={self.id}, item={self.item_id}, "
            f"unit='{self.unit_name}', factor={self.conversion_factor})>"
        )
