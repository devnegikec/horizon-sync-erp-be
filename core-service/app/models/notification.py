"""In-app notification model for WMS/ASN events"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text

from app.database import Base
from app.models.base import NotificationType
from app.models.types import JSONB, UUID


class Notification(Base):
    """In-app notification for warehouse and ASN events."""

    __tablename__ = "notifications"
    __audited__ = False

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Recipient
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Notification content
    type = Column(
        Enum(
            NotificationType,
            name="notificationtype",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Link to the entity that triggered the notification
    entity_type = Column(String(50), nullable=True, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    entity_no = Column(String(100), nullable=True)

    # Warehouse context (for filtering by assigned warehouse)
    warehouse_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Read state
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Sender info (for display)
    sender_id = Column(UUID(as_uuid=True), nullable=True)
    sender_name = Column(String(255), nullable=True)

    # Extra metadata
    extra_data = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    def __repr__(self):
        return (
            f"<Notification(id={self.id}, type={self.type}, "
            f"user_id={self.user_id}, is_read={self.is_read})>"
        )
