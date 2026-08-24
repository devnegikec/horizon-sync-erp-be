"""Vehicle and vehicle arrival models for inbound receiving.

A ``Vehicle`` is a physical truck/lorry that transports inbound goods.
A ``VehicleArrival`` records the event of a vehicle arriving at a warehouse
dock, optionally linked to one or more ASN orders (many-to-many via the
``vehicle_arrival_asns`` association table).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID

# Many-to-many association between a vehicle arrival and the ASN orders it carries.
# One vehicle may carry multiple ASNs; one ASN may arrive via multiple vehicles.
vehicle_arrival_asns = Table(
    "vehicle_arrival_asns",
    Base.metadata,
    Column(
        "vehicle_arrival_id",
        UUID(as_uuid=True),
        ForeignKey("vehicle_arrivals.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "asn_order_id",
        UUID(as_uuid=True),
        ForeignKey("asn_orders.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Vehicle(Base):
    """A truck/vehicle used to transport inbound goods."""

    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    vehicle_no = Column(String(100), nullable=False)
    driver_name = Column(String(255), nullable=True)
    driver_contact = Column(String(50), nullable=True)
    transporter = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "vehicle_no", name="uq_vehicle_org_vehicle_no"
        ),
    )

    arrivals = relationship(
        "VehicleArrival", back_populates="vehicle", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Vehicle(id={self.id}, vehicle_no='{self.vehicle_no}')>"


class VehicleArrival(Base):
    """An inbound vehicle arrival event at a warehouse dock."""

    __tablename__ = "vehicle_arrivals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="SET NULL"),
        nullable=True,
    )
    dock = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="arrived")
    arrived_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    notes = Column(Text, nullable=True)

    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    vehicle = relationship("Vehicle", back_populates="arrivals")
    warehouse = relationship("Warehouse")
    asn_orders = relationship("AsnOrder", secondary=vehicle_arrival_asns)
    receiving_slips = relationship("ReceivingSlip", back_populates="vehicle_arrival")

    def __repr__(self):
        return (
            f"<VehicleArrival(id={self.id}, vehicle_id={self.vehicle_id}, "
            f"status={self.status})>"
        )
