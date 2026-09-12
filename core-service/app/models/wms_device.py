"""WMS Device model for warehouse device management"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class WMSDeviceStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class WMSDevice(Base):
    """Warehouse device (scanner, tablet, etc.) assigned to workers."""

    __tablename__ = "wms_devices"
    __audited__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)
    device_code = Column(String(100), nullable=False, index=True)
    device_type = Column(String(100), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    serial_number = Column(String(255), nullable=True)
    os_version = Column(String(100), nullable=True)

    assigned_to_worker_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    status = Column(
        Enum(WMSDeviceStatus, name="wmsdevicestatus", create_type=False, values_callable=lambda o: [e.value for e in o]),
        nullable=False,
        default=WMSDeviceStatus.ACTIVE,
    )
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    extra_data = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    created_by = Column(UUID(as_uuid=True), nullable=True)

    # Relationships
    warehouse = relationship("Warehouse")

    def __repr__(self):
        return f"<WMSDevice(id={self.id}, code={self.device_code}, name={self.name})>"
