"""Put-away list and put-away list item models for inbound put-away workflow"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class PutAwayList(Base):
    """Put-away list generated from an approved receiving slip."""

    __tablename__ = "put_away_lists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id"),
        nullable=False,
        index=True,
    )
    put_away_list_no = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    receiving_slip_id = Column(
        UUID(as_uuid=True),
        ForeignKey("receiving_slips.id"),
        nullable=True,
        index=True,
    )
    remarks = Column(Text, nullable=True)
    assigned_to = Column(UUID(as_uuid=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    warehouse = relationship("Warehouse")
    receiving_slip = relationship("ReceivingSlip", back_populates="put_away_lists")
    items = relationship(
        "PutAwayListItem", back_populates="put_away_list", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<PutAwayList(id={self.id}, no={self.put_away_list_no}, "
            f"status={self.status})>"
        )


class PutAwayListItem(Base):
    """Individual items in a put-away list with bin location assignments."""

    __tablename__ = "put_away_list_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    put_away_list_id = Column(
        UUID(as_uuid=True),
        ForeignKey("put_away_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id"),
        nullable=False,
        index=True,
    )
    sku = Column(String(100), nullable=True)
    batch_number = Column(String(100), nullable=True)
    quantity = Column(Numeric(15, 3), nullable=False)
    bin_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_locations.id"),
        nullable=True,
        index=True,
    )
    sort_order = Column(Integer, default=0)
    status = Column(String(20), nullable=False, default="pending", index=True)
    notes = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    put_away_list = relationship("PutAwayList", back_populates="items")
    item = relationship("Item")
    bin_location = relationship("WarehouseLocation")

    def __repr__(self):
        return (
            f"<PutAwayListItem(id={self.id}, item={self.item_id}, "
            f"qty={self.quantity}, status={self.status})>"
        )
