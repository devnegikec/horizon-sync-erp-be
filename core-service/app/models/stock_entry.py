"""Stock entry and stock_entry_items models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from app.models.types import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import StockEntryStatus, StockEntryType
from app.models.types import JSONB


class StockEntry(Base):
    """Stock movement entry (receipt, issue, transfer, etc.)"""

    __tablename__ = "stock_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    stock_entry_no = Column(String(100), nullable=False, index=True)
    stock_entry_type = Column(
        Enum(
            StockEntryType,
            name="stockentrytype",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        nullable=False,
    )
    from_warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="SET NULL"),
        nullable=True,
    )
    to_warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="SET NULL"),
        nullable=True,
    )

    posting_date = Column(DateTime(timezone=True), nullable=False)
    posting_time = Column(String(10), nullable=True)
    status = Column(
        Enum(
            StockEntryStatus,
            name="stockentrystatus",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        nullable=True,
    )

    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    remarks = Column(Text, nullable=True)
    total_value = Column(Numeric(15, 2), nullable=True)
    expense_account_id = Column(UUID(as_uuid=True), nullable=True)
    cost_center_id = Column(UUID(as_uuid=True), nullable=True)
    is_backflush = Column(Boolean, nullable=True)
    bom_id = Column(UUID(as_uuid=True), nullable=True)
    extra_data = Column(JSONB, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)

    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse = relationship("Warehouse", foreign_keys=[to_warehouse_id])
    items = relationship(
        "StockEntryItem",
        back_populates="stock_entry",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<StockEntry(id={self.id}, no='{self.stock_entry_no}', type={self.stock_entry_type})>"


class StockEntryItem(Base):
    """Line item for a stock entry"""

    __tablename__ = "stock_entry_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    stock_entry_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stock_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="SET NULL"),
        nullable=True,
    )

    qty = Column(Numeric(15, 3), nullable=False)
    uom = Column(String(50), nullable=False)
    basic_rate = Column(Numeric(15, 2), nullable=True)
    basic_amount = Column(Numeric(15, 2), nullable=True)
    valuation_rate = Column(Numeric(15, 2), nullable=True)
    batch_no = Column(String(100), nullable=True)
    serial_nos = Column(JSONB, nullable=True)  # list of serial no strings
    quality_inspection_id = Column(UUID(as_uuid=True), nullable=True)
    description = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    stock_entry = relationship("StockEntry", back_populates="items")
    item = relationship("Item", backref="stock_entry_items")

    def __repr__(self):
        return f"<StockEntryItem(id={self.id}, stock_entry_id={self.stock_entry_id}, item_id={self.item_id}, qty={self.qty})>"
