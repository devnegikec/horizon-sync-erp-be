"""Stock settings model - one per organization"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class StockSettings(Base):
    """Organization-level stock management settings"""

    __tablename__ = "stock_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True
    )

    item_naming_by = Column(String(50), nullable=True)
    item_naming_series = Column(String(100), nullable=True)
    stock_entry_naming_series = Column(String(100), nullable=True)
    delivery_note_naming_series = Column(String(100), nullable=True)
    purchase_receipt_naming_series = Column(String(100), nullable=True)

    default_warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="SET NULL"),
        nullable=True,
    )

    allow_negative_stock = Column(Boolean, nullable=True)
    over_delivery_receipt_allowance = Column(Numeric(5, 2), nullable=True)
    over_billing_allowance = Column(Numeric(5, 2), nullable=True)
    auto_indent = Column(Boolean, nullable=True)
    auto_indent_notification = Column(JSONB, nullable=True)

    default_valuation_method = Column(String(50), nullable=True)
    auto_create_serial_no = Column(Boolean, nullable=True)
    default_quality_inspection_template_id = Column(UUID(as_uuid=True), nullable=True)

    stock_frozen_upto = Column(String(50), nullable=True)
    stock_frozen_upto_days = Column(Integer, nullable=True)
    show_barcode_field = Column(Boolean, nullable=True)
    convert_item_desc_to_transaction_desc = Column(Boolean, nullable=True)

    extra_data = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)

    default_warehouse = relationship("Warehouse", foreign_keys=[default_warehouse_id])

    def __repr__(self):
        return f"<StockSettings(organization_id={self.organization_id})>"
