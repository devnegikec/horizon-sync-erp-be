"""Stock level model - current quantity per item per warehouse"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class StockLevel(Base):
    """Current stock level for an item (product) in a warehouse"""

    __tablename__ = "stock_levels"
    __table_args__ = (
        UniqueConstraint(
            "product_id", "warehouse_id", name="uq_stock_levels_product_warehouse"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
    )  # references items.id
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
    )

    quantity_on_hand = Column(Integer, nullable=True, default=0)
    quantity_reserved = Column(Integer, nullable=True, default=0)
    quantity_available = Column(Integer, nullable=True, default=0)  # on_hand - reserved

    last_counted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    product = relationship("Item", backref="stock_levels")
    warehouse = relationship("Warehouse", backref="stock_levels")

    def __repr__(self):
        return f"<StockLevel(product_id={self.product_id}, warehouse_id={self.warehouse_id}, qty={self.quantity_on_hand})>"
