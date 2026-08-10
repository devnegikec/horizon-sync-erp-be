"""QR Activation Parameters and Tracks models"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class QRActivationParameters(Base):
    """QR activation parameters per block/product"""

    __tablename__ = "qr_activation_parameters"

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
    qr_settings = Column(Boolean, default=False)
    qr_cascade = Column(Boolean, default=False)
    extra_data = Column(JSONB, nullable=True)

    parent_id = Column(UUID(as_uuid=True), ForeignKey("qr_activation_tracks.id"), nullable=True)
    parent_app_id = Column(UUID(as_uuid=True), ForeignKey("qr_activation_tracks.id"), nullable=True)


    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)


    parent = relationship("QRActivationTrack", foreign_keys=[parent_id])
    parent_app = relationship("QRActivationTrack", foreign_keys=[parent_app_id])


    def __repr__(self):
        return f"<QRActivationParameters(id={self.id}, product_id={self.product_id})>"



class QRTypeEnum(str,enum.Enum):
    shipper = "shipper"
    pallet = "pallet"
    container = "container"

class QRActivationTrack(Base):
    __tablename__ = "qr_activation_tracks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    qr_type = Column(Enum(QRTypeEnum,name="qr_type_enum",
        values_callable=lambda enum: [e.value for e in enum],   native_enum=True),
    nullable=True)
    name = Column(String(20), nullable=True)
    capacity = Column(Integer, nullable=True)
    serial_number = Column(String(10), nullable=True, index=True)
    app_cascade_map = Column(Boolean, default=False)
    qr_code_link = Column(String(600), nullable=True)

    # Self-referential — dashboard hierarchy
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("qr_activation_tracks.id"),
        nullable=True,
    )
    # App hierarchy
    parent_app_id = Column(
        UUID(as_uuid=True),
        ForeignKey("qr_activation_tracks.id"),
        nullable=True,
    )

    # Audit
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    parent = relationship(
        "QRActivationTrack",
        foreign_keys=[parent_id],
        remote_side="QRActivationTrack.id",
        backref="child_items",
    )
    parent_app = relationship(
        "QRActivationTrack",
        foreign_keys=[parent_app_id],
        remote_side="QRActivationTrack.id",
        backref="app_childs",
    )

    def __repr__(self):
        return f"<QRActivationTrack(id={self.id}, name='{self.name}', type='{self.qr_type}')>"




# class QRActivationTrack(Base):
#     """QR activation track — hierarchical cascade structure"""

#     __tablename__ = "qr_activation_tracks"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
#     qr_type = Column(String(25), nullable=True)
#     name = Column(String(20), nullable=True)
#     capacity = Column(Integer, nullable=True)
#     serial_number = Column(String(10), nullable=True)
#     qr_code_link = Column(Text, nullable=True)
#     app_cascade_map = Column(Boolean, default=False)
#     parent_id = Column(UUID(as_uuid=True),
#                        ForeignKey("qr_activation_tracks.id"), nullable=True)
#     parent_app_id = Column(UUID(as_uuid=True),
#                            ForeignKey("qr_activation_tracks.id"), nullable=True)
#     created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

#     # Self-referential relationships
#     children = relationship(
#         "QRActivationTrack",
#         foreign_keys=[parent_id],
#         backref="parent",
#         remote_side=[id],
#     )

#     def __repr__(self):


#         return f"<QRActivationTrack(id={self.id}, name='{self.name}')>"
