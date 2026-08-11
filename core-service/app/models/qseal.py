"""QSeal Activation Parameters and Tracks models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class QSealParameters(Base):
    """QSeal activation parameters per block/product — individual unit metadata"""

    __tablename__ = "qseal_parameters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("qr_products.id"), nullable=True)
    block_id = Column(UUID(as_uuid=True), ForeignKey("qr_blocks.id"), nullable=True)
    serial_number = Column(String(75), nullable=True)
    manufacturing_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    manufacturing_unit = Column(String(100), nullable=False)
    dispatch_batch = Column(String(100), nullable=True)
    destination_market = Column(String(100), nullable=True)
    mrp = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(10), nullable=True)
    batch_size = Column(Integer, nullable=True)
    qseal_settings = Column(Boolean, default=False)
    qseal_cascade = Column(Boolean, default=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("qseal_tracks.id"), nullable=True)
    parent_app_id = Column(
        UUID(as_uuid=True), ForeignKey("qseal_tracks.id"), nullable=True
    )
    extra_data = Column(JSONB, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    def __repr__(self):
        return f"<QSealParameters(id={self.id}, product_id={self.product_id})>"


class QSealTrack(Base):
    """QSeal activation track — hierarchical cascade structure (shipper / pallet / container)"""

    __tablename__ = "qseal_tracks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    qseal_type = Column(String(25), nullable=True)
    name = Column(String(20), nullable=True)
    capacity = Column(Integer, nullable=True)
    serial_number = Column(String(10), nullable=True)
    qseal_code_link = Column(Text, nullable=True)
    app_cascade_map = Column(Boolean, default=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("qseal_tracks.id"), nullable=True)
    parent_app_id = Column(
        UUID(as_uuid=True), ForeignKey("qseal_tracks.id"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Self-referential relationships
    children = relationship(
        "QSealTrack",
        foreign_keys=[parent_id],
        backref="parent",
        remote_side=[id],
    )

    def __repr__(self):
        return f"<QSealTrack(id={self.id}, name='{self.name}')>"
