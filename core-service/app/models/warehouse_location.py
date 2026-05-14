"""Warehouse Location model and related enums for bin-level storage tracking"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


# ===========================================
# WAREHOUSE BIN MANAGEMENT ENUMS
# ===========================================


class LocationType(str, enum.Enum):
    """Location type in the warehouse hierarchy"""

    ZONE = "zone"
    AISLE = "aisle"
    BAY = "bay"
    LEVEL = "level"
    BIN = "bin"


class PutAwayListStatus(str, enum.Enum):
    """Put-away list status enumeration"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PutAwayListItemStatus(str, enum.Enum):
    """Put-away list item status enumeration"""

    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class WorkerTaskType(str, enum.Enum):
    """Worker task type enumeration"""

    PUT_AWAY = "put_away"
    PICK = "pick"


class WorkerTaskStatus(str, enum.Enum):
    """Worker task status enumeration"""

    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ScanType(str, enum.Enum):
    """QR scan type enumeration"""

    START = "start"
    FINISH = "finish"


class AllocationType(str, enum.Enum):
    """Location allocation type enumeration"""

    EXCLUSIVE = "exclusive"
    PREFERRED = "preferred"


# ===========================================
# WAREHOUSE LOCATION MODEL
# ===========================================


class WarehouseLocation(Base):
    """Warehouse location hierarchy model (Zone → Aisle → Bay → Level → Bin)"""

    __tablename__ = "warehouse_locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_locations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    location_type = Column(
        Enum(
            LocationType,
            name="locationtype",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    code = Column(String(50), nullable=False)
    full_code = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    total_capacity = Column(Integer, default=0)
    capacity_uom = Column(String(50), nullable=True)
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Audit fields
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint("warehouse_id", "full_code", name="uq_location_code_warehouse"),
    )

    # Relationships
    parent = relationship("WarehouseLocation", remote_side=[id], backref="children")
    warehouse = relationship("Warehouse", backref="locations")

    def __repr__(self):
        return f"<WarehouseLocation(id={self.id}, code='{self.full_code}', type='{self.location_type}')>"
