"""Warehouse model definition"""

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
from app.models.base import WarehouseType
from app.models.types import JSONB, UUID


class Warehouse(Base):
    """Extended Warehouse model for inventory management"""

    __tablename__ = "warehouses_extended"
    __audited__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Basic Information
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Hierarchy
    parent_warehouse_id = Column(
        UUID(as_uuid=True), ForeignKey("warehouses_extended.id"), nullable=True
    )
    warehouse_type = Column(
        Enum(
            WarehouseType,
            name="warehousetype",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=WarehouseType.WAREHOUSE,
    )

    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)

    # Contact
    contact_name = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    contact_email = Column(String(255), nullable=True)

    # Capacity
    total_capacity = Column(Integer, nullable=True)
    capacity_uom = Column(String(50), nullable=True)

    # Capacity planning — dimension toggles & threshold defaults
    use_volume = Column(Boolean, nullable=False, default=True)
    use_weight = Column(Boolean, nullable=False, default=False)
    full_threshold_pct = Column(Numeric(5, 3), nullable=False, default=0.90)
    almost_full_threshold_pct = Column(Numeric(5, 3), nullable=False, default=0.70)

    # Accounting
    stock_account_id = Column(UUID(as_uuid=True), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

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
    parent = relationship("Warehouse", remote_side=[id], backref="children")

    def __repr__(self):
        return f"<Warehouse(id={self.id}, code='{self.code}', name='{self.name}')>"
