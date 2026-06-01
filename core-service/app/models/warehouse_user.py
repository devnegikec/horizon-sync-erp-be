"""Warehouse-user assignment model for role-based warehouse access"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String

from app.database import Base
from app.models.base import WarehouseUserRole
from app.models.types import JSONB, UUID


class WarehouseUser(Base):
    """Links a user to a warehouse with a specific operational role.

    Used for:
      - Filtering warehouse lists (supervisor sees assigned warehouses only,
        unless user has mother-warehouse access via extra_data or a different role)
      - Routing ASN notifications to the correct warehouse users
      - Task assignment (pick, put-away, gate verification)
    """

    __tablename__ = "warehouse_users"
    __audited__ = False

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
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

    # If true, this user can see ALL warehouses regardless of assignments
    # (typically set for mother-warehouse supervisors via extra_data or a system flag)
    is_primary = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    extra_data = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self):
        return (
            f"<WarehouseUser(user_id={self.user_id}, "
            f"warehouse_id={self.warehouse_id}, role={self.role})>"
        )
