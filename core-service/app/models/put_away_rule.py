"""Put away rule model"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from app.models.types import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB


class PutAwayRule(Base):
    """Rule for automated put-away of items to warehouse locations"""

    __tablename__ = "put_away_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=True,
    )
    item_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("item_groups.id", ondelete="CASCADE"),
        nullable=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
    )

    capacity = Column(Integer, nullable=True)
    priority = Column(Integer, nullable=True)
    min_qty = Column(Integer, nullable=True)
    max_qty = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=True, default=True)
    extra_data = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)

    item = relationship("Item", backref="put_away_rules")
    item_group = relationship("ItemGroup", backref="put_away_rules")
    warehouse = relationship("Warehouse", backref="put_away_rules")

    def __repr__(self):
        return f"<PutAwayRule(id={self.id}, name='{self.name}', warehouse_id={self.warehouse_id})>"
