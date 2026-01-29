"""Delivery note and delivery note items models"""

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import DocumentStatus
from app.models.types import JSONB


class DeliveryNote(Base):
    __tablename__ = "delivery_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    delivery_note_no = Column(String(100), nullable=False)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    delivery_date = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    status = Column(
        Enum(
            DocumentStatus,
            name="documentstatus",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=DocumentStatus.DRAFT,
        nullable=False,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="SET NULL"),
        nullable=True,
    )
    pick_list_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pick_lists.id", ondelete="SET NULL"),
        nullable=True,
    )
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    remarks = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    items = relationship(
        "DeliveryNoteItem", back_populates="delivery_note", cascade="all, delete-orphan"
    )


class DeliveryNoteItem(Base):
    __tablename__ = "delivery_note_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    delivery_note_id = Column(
        UUID(as_uuid=True),
        ForeignKey("delivery_notes.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    qty = Column(Numeric(15, 3), nullable=False)
    uom = Column(String(50), nullable=False)
    rate = Column(Numeric(15, 2), nullable=True)
    amount = Column(Numeric(15, 2), nullable=True)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="SET NULL"),
        nullable=True,
    )
    batch_no = Column(String(100), nullable=True)
    serial_nos = Column(JSONB, nullable=True)
    sort_order = Column(Integer, default=0)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    delivery_note = relationship("DeliveryNote", back_populates="items")
