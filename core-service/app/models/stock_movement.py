"""Stock movement model - audit trail of stock changes"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from app.models.types import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import MovementType


class StockMovement(Base):
    """Record of a stock movement (in, out, transfer, adjustment)"""

    __tablename__ = "stock_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
    )

    movement_type = Column(
        Enum(
            MovementType,
            name="movementtype",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        nullable=False,
    )
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(15, 2), nullable=True)

    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(Text, nullable=True)
    performed_by = Column(UUID(as_uuid=True), nullable=True)
    performed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    product = relationship("Item", backref="stock_movements")
    warehouse = relationship("Warehouse", backref="stock_movements")

    def __repr__(self):
        return f"<StockMovement(id={self.id}, product_id={self.product_id}, type={self.movement_type}, qty={self.quantity})>"
