"""Product model — shared catalog core (always exists for every customer type)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class Product(Base):
    """Shared catalog identity.

    One product record exists for every sellable thing, regardless of whether
    the organization uses WMS (items), Qseal (qr_products), or both. Module
    extensions reference this core via FK — no fields are duplicated here.
    """

    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=True, index=True)
    gtin = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)

    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True)
    # No FK yet — product categories master is a later phase.
    category_id = Column(UUID(as_uuid=True), nullable=True)

    # wms | qseal | both — derived from which module extensions exist.
    product_type = Column(String(20), nullable=True)

    images = Column(JSONB, nullable=True)
    tags = Column(JSONB, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    brand = relationship("Brand", foreign_keys=[brand_id])

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', sku='{self.sku}')>"
