"""WMS Worker model for warehouse worker management with barcode login"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class WMSWorkerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"


class WMSWorker(Base):
    """Warehouse worker with optional barcode-based login."""

    __tablename__ = "wms_workers"
    __audited__ = True
    __audit_exclude__ = {"password_hash", "barcode"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    display_name = Column(String(200), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True)

    # Login credentials
    login_username = Column(String(100), nullable=True, unique=True)
    password_hash = Column(String(255), nullable=True)

    # Barcode for quick login
    barcode = Column(String(100), nullable=True, index=True, unique=True)

    # Human-readable employee identifier (unique per org, assigned at creation)
    employee_id = Column(String(100), nullable=True, index=True)

    role = Column(String(50), nullable=False, default="warehouse_worker")
    status = Column(
        Enum(WMSWorkerStatus, name="wmsworkerstatus", create_type=False, values_callable=lambda o: [e.value for e in o]),
        nullable=False,
        default=WMSWorkerStatus.ACTIVE,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

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
    devices = relationship("WMSDevice", back_populates="assigned_worker", foreign_keys="WMSDevice.assigned_to_worker_id")

    def __repr__(self):
        return f"<WMSWorker(id={self.id}, name={self.display_name or self.first_name}, barcode={self.barcode})>"
