"""Warranty models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class WarrantyPeriod(Base):
    __tablename__ = "warranty_periods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    months = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    def __repr__(self):
        return f"<WarrantyPeriod(id={self.id}, months={self.months})>"


class Warranty(Base):
    __tablename__ = "warranties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    product_item_id = Column(UUID(as_uuid=True),
                             ForeignKey("product_items.id"), nullable=True)
    serial_number = Column(String(120), nullable=True, index=True)
    customer_name = Column(String(255), nullable=False)
    mobile = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    location = Column(String(120), nullable=True)
    ip = Column(String(120), nullable=True)
    purchase_date = Column(Date, nullable=True)
    warranty_valid_till = Column(DateTime(timezone=True), nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    product_item = relationship("ProductItem")

    def __repr__(self):
        return f"<Warranty(id={self.id}, serial='{self.serial_number}')>"
