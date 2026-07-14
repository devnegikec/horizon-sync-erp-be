"""Quality inspection template, parameters, inspections, and readings models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import InspectionStatus, InspectionType, ReadingType
from app.models.types import JSONB, UUID


class QualityInspectionTemplate(Base):
    __tablename__ = "quality_inspection_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="SET NULL"), nullable=True
    )
    item_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("item_groups.id", ondelete="SET NULL"),
        nullable=True,
    )
    inspection_type = Column(
        Enum(
            InspectionType,
            name="inspectiontype",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=InspectionType.INCOMING,
        nullable=False,
    )
    is_active = Column(Boolean, default=True)
    extra_data = Column(JSONB, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    parameters = relationship(
        "QualityInspectionParameter",
        back_populates="template",
        cascade="all, delete-orphan",
    )


class QualityInspectionParameter(Base):
    __tablename__ = "quality_inspection_parameters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("quality_inspection_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    parameter_name = Column(String(255), nullable=False)
    reading_type = Column(
        Enum(
            ReadingType,
            name="readingtype",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=ReadingType.NUMERIC,
        nullable=False,
    )
    numeric_min = Column(Numeric(15, 4), nullable=True)
    numeric_max = Column(Numeric(15, 4), nullable=True)
    uom = Column(String(50), nullable=True)
    specification = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    template = relationship("QualityInspectionTemplate", back_populates="parameters")


class QualityInspection(Base):
    __tablename__ = "quality_inspections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    inspection_no = Column(String(100), nullable=False)
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("quality_inspection_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    batch_no = Column(String(100), nullable=True)
    serial_no = Column(String(100), nullable=True)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="SET NULL"),
        nullable=True,
    )
    inspection_type = Column(
        Enum(
            InspectionType,
            name="inspectiontype",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=InspectionType.INCOMING,
        nullable=False,
    )
    status = Column(
        Enum(
            InspectionStatus,
            name="inspectionstatus",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=InspectionStatus.PENDING,
        nullable=False,
    )
    inspection_date = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
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

    readings = relationship(
        "QualityInspectionReading",
        back_populates="inspection",
        cascade="all, delete-orphan",
    )


class QualityInspectionReading(Base):
    __tablename__ = "quality_inspection_readings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    inspection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("quality_inspections.id", ondelete="CASCADE"),
        nullable=False,
    )
    parameter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("quality_inspection_parameters.id", ondelete="CASCADE"),
        nullable=False,
    )
    reading_value_numeric = Column(Numeric(15, 4), nullable=True)
    reading_value_text = Column(Text, nullable=True)
    reading_value_pass_fail = Column(Boolean, nullable=True)
    result = Column(String(50), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    inspection = relationship("QualityInspection", back_populates="readings")
