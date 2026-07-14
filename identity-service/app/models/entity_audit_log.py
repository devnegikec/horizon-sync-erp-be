"""Entity-level audit trail model for tracking CRUD operations on audited models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, JSON, String, Text, Uuid

from app.database import Base


class EntityAuditLog(Base):
    """Stores field-level before/after snapshots of every data mutation."""

    __tablename__ = "entity_audit_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, nullable=True, index=True)
    organization_id = Column(Uuid, nullable=True, index=True)
    action = Column(String(10), nullable=False)
    table_name = Column(String(100), nullable=False)
    record_id = Column(Uuid, nullable=False)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    changed_fields = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("idx_entity_audit_table_record", "table_name", "record_id"),
        Index("idx_entity_audit_action", "action"),
        Index("idx_entity_audit_created_at", "created_at"),
    )
