"""Item Group model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from app.models.types import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import ValuationMethod
from app.models.types import JSONB


class ItemGroup(Base):
    """Item Group model for categorizing items"""

    __tablename__ = "item_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)

    parent_id = Column(UUID(as_uuid=True), ForeignKey("item_groups.id"), nullable=True)
    default_valuation_method = Column(
        Enum(
            ValuationMethod,
            name="valuationmethod",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    default_uom = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)

    # Tax Templates
    sales_tax_template_id = Column(
        UUID(as_uuid=True), ForeignKey("tax_templates.id"), nullable=True
    )
    purchase_tax_template_id = Column(
        UUID(as_uuid=True), ForeignKey("tax_templates.id"), nullable=True
    )

    # Extra
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
    parent = relationship("ItemGroup", remote_side=[id], backref="children")
    items = relationship("Item", back_populates="item_group")
    sales_tax_template = relationship(
        "TaxTemplate", foreign_keys=[sales_tax_template_id], lazy="select"
    )
    purchase_tax_template = relationship(
        "TaxTemplate", foreign_keys=[purchase_tax_template_id], lazy="select"
    )

    def __repr__(self):
        return f"<ItemGroup(id={self.id}, code='{self.code}', name='{self.name}')>"
