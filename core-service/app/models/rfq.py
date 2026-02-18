"""RFQ (Request for Quotation) model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from app.models.types import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import RFQStatus
from app.models.types import JSONB


class RFQ(Base):
    """RFQ (Request for Quotation) model for procurement workflow"""

    __tablename__ = "rfqs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Reference to Material Request
    material_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("material_requests.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)

    # Status
    status = Column(
        Enum(
            RFQStatus,
            name="rfqstatus",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=RFQStatus.DRAFT,
        nullable=False,
    )

    # Closing date
    closing_date = Column(Date, nullable=False)

    # Extra
    extra_data = Column(JSONB, nullable=True)

    # Audit fields
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    line_items = relationship("RFQLine", back_populates="rfq", cascade="all, delete-orphan")
    suppliers = relationship("RFQSupplier", back_populates="rfq", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RFQ(id={self.id}, status='{self.status}')>"


class RFQLine(Base):
    """RFQ Line Item model"""

    __tablename__ = "rfq_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    rfq_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Quantity and details
    quantity = Column(Numeric(15, 4), nullable=False)
    required_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)

    # Extra
    extra_data = Column(JSONB, nullable=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    rfq = relationship("RFQ", back_populates="line_items")
    quotes = relationship("SupplierQuote", back_populates="rfq_line", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RFQLine(id={self.id}, item_id={self.item_id}, quantity={self.quantity})>"


class RFQSupplier(Base):
    """RFQ Supplier junction table"""

    __tablename__ = "rfq_suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    rfq_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_id = Column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Audit fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    rfq = relationship("RFQ", back_populates="suppliers")

    def __repr__(self):
        return f"<RFQSupplier(rfq_id={self.rfq_id}, supplier_id={self.supplier_id})>"


class SupplierQuote(Base):
    """Supplier Quote model for RFQ responses"""

    __tablename__ = "supplier_quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    rfq_line_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rfq_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_id = Column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Quote details
    quoted_price = Column(Numeric(15, 2), nullable=False)
    quoted_delivery_date = Column(Date, nullable=False)
    supplier_notes = Column(Text, nullable=True)

    # Extra
    extra_data = Column(JSONB, nullable=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    rfq_line = relationship("RFQLine", back_populates="quotes")

    def __repr__(self):
        return f"<SupplierQuote(id={self.id}, supplier_id={self.supplier_id}, quoted_price={self.quoted_price})>"
