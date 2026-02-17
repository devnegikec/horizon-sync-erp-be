"""Serial number and serial_no_history models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from app.models.types import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB


class SerialNo(Base):
    """Serial number tracking for items in a warehouse"""

    __tablename__ = "serial_nos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    serial_no = Column(String(100), nullable=False, index=True)
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
    )

    status = Column(String(50), nullable=True)

    purchase_date = Column(DateTime(timezone=True), nullable=True)
    purchase_rate = Column(Numeric(15, 2), nullable=True)
    supplier_id = Column(UUID(as_uuid=True), nullable=True)

    delivery_date = Column(DateTime(timezone=True), nullable=True)
    customer_id = Column(UUID(as_uuid=True), nullable=True)

    warranty_period = Column(Integer, nullable=True)
    warranty_expiry_date = Column(DateTime(timezone=True), nullable=True)
    amc_expiry_date = Column(DateTime(timezone=True), nullable=True)

    batch_no = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    item = relationship("Item", backref="serial_nos")
    warehouse = relationship("Warehouse", backref="serial_nos")
    history = relationship(
        "SerialNoHistory",
        back_populates="serial_no",
        order_by="SerialNoHistory.transaction_date",
    )

    def __repr__(self):
        return f"<SerialNo(id={self.id}, serial_no='{self.serial_no}', item_id={self.item_id})>"


class SerialNoHistory(Base):
    """History of serial number movements/transactions"""

    __tablename__ = "serial_no_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    serial_no_id = Column(
        UUID(as_uuid=True),
        ForeignKey("serial_nos.id", ondelete="CASCADE"),
        nullable=False,
    )

    transaction_type = Column(String(50), nullable=False)
    transaction_id = Column(UUID(as_uuid=True), nullable=True)

    from_warehouse_id = Column(UUID(as_uuid=True), nullable=True)
    to_warehouse_id = Column(UUID(as_uuid=True), nullable=True)

    transaction_date = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    remarks = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    serial_no = relationship("SerialNo", back_populates="history")

    def __repr__(self):
        return f"<SerialNoHistory(id={self.id}, serial_no_id={self.serial_no_id}, type='{self.transaction_type}')>"
