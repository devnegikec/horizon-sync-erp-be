"""Warehouse Location model and related enums for bin-level storage tracking"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
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


class ScanSessionType(str, enum.Enum):
    """Scan session type enumeration"""

    INBOUND = "inbound"
    GATE = "gate"


class ScanSessionStatus(str, enum.Enum):
    """Scan session status enumeration"""

    OPEN = "open"
    CLOSED = "closed"


class ReceivingSlipStatus(str, enum.Enum):
    """Receiving slip status enumeration"""

    PENDING_REVIEW = "pending_review"
    PENDING_PUTAWAY = "pending_putaway"
    PUTAWAY_COMPLETE = "putaway_complete"
    REJECTED = "rejected"


class ReceivingSlipItemFlag(str, enum.Enum):
    """Receiving slip item flag enumeration"""

    OK = "ok"
    SHORT = "short"
    DAMAGED = "damaged"


class GateVerificationStatus(str, enum.Enum):
    """Gate verification session status enumeration"""

    OPEN = "open"
    VERIFIED = "verified"
    CANCELLED = "cancelled"


class GateVerificationItemStatus(str, enum.Enum):
    """Gate verification item status enumeration"""

    VERIFIED = "verified"
    UNAUTHORIZED = "unauthorized"


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
    location_type = Column(String(20), nullable=False)
    code = Column(String(50), nullable=False)
    full_path = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    capacity = Column(Numeric(15, 3), default=0)
    total_capacity = Column(Numeric(15, 3), default=0)
    available_capacity = Column(Numeric(15, 3), default=0)
    capacity_uom = Column(String(50), nullable=True)
    position_x = Column(Numeric(10, 2), default=0)
    position_y = Column(Numeric(10, 2), default=0)
    max_volume_cc = Column(Numeric(15, 2), nullable=True)
    max_weight_grams = Column(Numeric(15, 2), nullable=True)
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("warehouse_id", "full_path", name="idx_wl_warehouse_path"),
    )

    # Relationships
    parent = relationship("WarehouseLocation", remote_side=[id], backref="children")
    warehouse = relationship("Warehouse", backref="locations")
    bin_stock_levels = relationship("BinStockLevel", back_populates="bin_location")
    allocations = relationship("LocationAllocation", back_populates="location")

    def __repr__(self):
        return f"<WarehouseLocation(id={self.id}, code='{self.full_path}', type='{self.location_type}')>"
