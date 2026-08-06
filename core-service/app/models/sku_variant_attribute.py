"""
Variant Attribute models.

These three models together implement the flexible variant system described
in the SKU design doc (Section 5).  No schema changes are needed when a new
product category is added — the brand team simply creates new Attributes and
their Values through the admin/API.

Hierarchy:
    VariantAttribute          e.g.  "Capacity (Litre)"
        └── VariantAttributeValue  e.g.  "1L", "1.5L", "2L"

    ProductSKUAttributeValue  — join table that links a ProductSKU to one or
                                more VariantAttributeValues so that:
                                    Fan + Sweep:1200mm + Color:White → FAN-1200-WHT
                                is two rows here, one per attribute value.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class VariantAttribute(Base):
    """
    An axis of variation — defines *what kind* of variant a product has.

    Examples:
        name="Capacity",  unit="Litre"   → for cookers, bottles, cooking oil
        name="Size",      unit=None       → for garments, boxes
        name="Color",     unit=None       → for fans, garments
        name="Sweep Size",unit="mm"       → for fans
        name="Pack Count",unit="Tablets"  → for pharma

    Attributes are defined per organisation and are reusable across all
    products in that org that share the same category of variation.
    """

    __tablename__ = "variant_attributes"
    __table_args__ = (
        # same attribute name must be unique within an organisation
        UniqueConstraint("organization_id", "name", name="uq_variant_attr_org_name"),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    name = Column(String(50),  nullable=False)   # "Capacity", "Size", "Color"
    unit = Column(String(20),  nullable=True)    # "Litre", "mm" — None for Size/Color

    # Audit
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    values = relationship("VariantAttributeValue",back_populates="attribute",
        cascade="all, delete-orphan",
        order_by="VariantAttributeValue.sort_order",)

    def __repr__(self):
        unit_str = f" ({self.unit})" if self.unit else ""
        return f"<VariantAttribute(name='{self.name}{unit_str}')>"


class VariantAttributeValue(Base):
    """
    A specific option on a VariantAttribute axis.

    Examples for Capacity:  value="1",     display_value="1 Litre"
                            value="1.5",   display_value="1.5 Litre"
                            value="5",     display_value="5 Litre"

    Examples for Size:      value="S",     display_value="Small"
                            value="L",     display_value="Large"
                            value="XL",    display_value="Extra Large"

    `value`         — used for logic, sorting, and SKU code generation.
    `display_value` — shown in the UI / on certs; falls back to `value` if None.
    `sort_order`    — controls the order options appear in dropdowns / pickers.
    """

    __tablename__ = "variant_attribute_values"
    __table_args__ = (
        # same value cannot exist twice under the same attribute
        UniqueConstraint("attribute_id", "value", name="uq_attr_value"),
    )

    id   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attribute_id = Column(UUID(as_uuid=True),ForeignKey("variant_attributes.id"),nullable=False,
        index=True,)

    value         = Column(String(50), nullable=False)   # "1", "S", "White"
    display_value = Column(String(50), nullable=True)    # "1 Litre", "Small", "White"
    sort_order    = Column(Integer,    default=0)

    # Audit
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    attribute = relationship("VariantAttribute", back_populates="values")
    sku_links  = relationship("ProductSKUAttributeValue", back_populates="attribute_value")

    @property
    def label(self):
        """Returns display_value if set, otherwise falls back to value."""
        return self.display_value or self.value

    def __repr__(self):
        return f"<VariantAttributeValue(value='{self.label}', attribute_id={self.attribute_id})>"


class ProductSKUAttributeValue(Base):
    """
    Join table — maps one ProductSKU to one VariantAttributeValue.

    A SKU with multiple attributes (e.g. Fan: Sweep Size + Color) will have
    multiple rows here, one per attribute value:

        sku_id=<FAN-1200-WHT>  attribute_value_id=<Sweep Size: 1200mm>
        sku_id=<FAN-1200-WHT>  attribute_value_id=<Color: White>

    The UniqueConstraint prevents the same attribute value from being linked
    to the same SKU more than once.  Application-level logic should also
    validate that no two SKUs under the same Product share an identical *set*
    of attribute values (e.g. you cannot have two "1L Pressure Cooker" SKUs).
    """

    __tablename__ = "product_sku_attribute_values"
    __table_args__ = (
        UniqueConstraint("sku_id", "attribute_value_id", name="uq_sku_attr_value"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku_id = Column(UUID(as_uuid=True),ForeignKey("product_skus.id"),nullable=False,index=True,)
    attribute_value_id  = Column(UUID(as_uuid=True),ForeignKey("variant_attribute_values.id"),
        nullable=False,index=True,)

    # Audit
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    sku             = relationship("ProductSKU",           back_populates="sku_attribute_values")
    attribute_value = relationship("VariantAttributeValue", back_populates="sku_links")

    def __repr__(self):
        return (
            f"<ProductSKUAttributeValue("
            f"sku_id={self.sku_id}, "
            f"attribute_value_id={self.attribute_value_id})>"
        )