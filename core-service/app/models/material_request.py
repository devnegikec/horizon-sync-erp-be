"""Material Request model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import MaterialRequestStatus
from app.models.types import JSONB


class MaterialRequest(Base):
    """Material Request model for procurement workflow"""

    __tablename__ = "material_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Status
    status = Column(
        Enum(
            MaterialRequestStatus,
            name="materialrequeststatus",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=MaterialRequestStatus.DRAFT,
        nullable=False,
    )

    # Notes
    notes = Column(Text, nullable=True)

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
    line_items = relationship(
        "MaterialRequestLine",
        back_populates="material_request",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<MaterialRequest(id={self.id}, status='{self.status}')>"


class MaterialRequestLine(Base):
    """Material Request Line Item model"""

    __tablename__ = "material_request_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    material_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("material_requests.id", ondelete="CASCADE"),
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
    material_request = relationship("MaterialRequest", back_populates="line_items")

    def __repr__(self):
        return f"<MaterialRequestLine(id={self.id}, item_id={self.item_id}, quantity={self.quantity})>"
