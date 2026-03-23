"""QR Scan Event model — replaces external Metamo integration"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class QRScanEvent(Base):
    """Records every QR code scan with device and geo data"""

    __tablename__ = "qr_scan_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    product_item_id = Column(UUID(as_uuid=True),
                             ForeignKey("product_items.id"), nullable=True)
    serial_number = Column(String(75), nullable=True, index=True)
    scan_timestamp = Column(DateTime(timezone=True),
                            default=lambda: datetime.now(UTC), index=True)
    device_type = Column(String(50), nullable=True)
    os = Column(String(50), nullable=True)
    browser = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    extra_data = Column(JSONB, nullable=True)

    # Relationships
    product_item = relationship("ProductItem", back_populates="scan_events")

    def __repr__(self):
        return f"<QRScanEvent(id={self.id}, serial='{self.serial_number}')>"
