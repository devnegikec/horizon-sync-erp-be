"""Pending warehouse-user assignment model

Stores warehouse assignments keyed by email before the invited user
has accepted their invitation and been assigned a user_id.

When the user eventually logs in and calls /my-warehouses,
these pending rows are resolved into actual warehouse_users rows.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String

from app.database import Base
from app.models.base import WarehouseUserRole
from app.models.types import UUID


class PendingWarehouseAssignment(Base):
    """Warehouse assignment waiting for the invited user to accept and log in."""

    __tablename__ = "pending_warehouse_assignments"
    __audited__ = False

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Email of the invited user (resolved to user_id on first login)
    email = Column(String(255), nullable=False, index=True)

    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
    )

    role = Column(
        Enum(
            WarehouseUserRole,
            name="warehouseuserrole",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        nullable=False,
        default=WarehouseUserRole.OPERATOR,
    )

    is_primary = Column(Boolean, default=False, nullable=False)

    # Who created this pending assignment
    created_by = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self):
        return (
            f"<PendingWarehouseAssignment(email={self.email}, "
            f"warehouse_id={self.warehouse_id}, role={self.role})>"
        )
