"""Stock reconciliation and items models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String, Text
from app.models.types import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import StockEntryStatus
from app.models.types import JSONB


class StockReconciliation(Base):
    """Stock reconciliation document header"""

    __tablename__ = "stock_reconciliations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    reconciliation_no = Column(String(100), nullable=False, index=True)
    purpose = Column(String(100), nullable=True)
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
    expense_account_id = Column(UUID(as_uuid=True), nullable=True)
    difference_account_id = Column(UUID(as_uuid=True), nullable=True)
    remarks = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)

    items = relationship(
        "StockReconciliationItem",
        back_populates="reconciliation",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<StockReconciliation(id={self.id}, no='{self.reconciliation_no}')>"


class StockReconciliationItem(Base):
    """Line item for a stock reconciliation"""

    __tablename__ = "stock_reconciliation_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    reconciliation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stock_reconciliations.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
    )

    current_qty = Column(Numeric(15, 3), nullable=True)
    qty = Column(Numeric(15, 3), nullable=False)
    qty_difference = Column(Numeric(15, 3), nullable=True)
    current_valuation_rate = Column(Numeric(15, 2), nullable=True)
    valuation_rate = Column(Numeric(15, 2), nullable=True)
    batch_no = Column(String(100), nullable=True)
    serial_nos = Column(JSONB, nullable=True)
    extra_data = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    reconciliation = relationship("StockReconciliation", back_populates="items")
    item = relationship("Item", backref="stock_reconciliation_items")

    def __repr__(self):
        return f"<StockReconciliationItem(id={self.id}, reconciliation_id={self.reconciliation_id}, item_id={self.item_id})>"
