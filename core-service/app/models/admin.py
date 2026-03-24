"""Admin portal models — activity logs, audit logs, notifications, feature flags"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)

from app.database import Base
from app.models.types import JSONB, UUID


class UserActivityLog(Base):
    """Tracks user actions: login, logout, page views, data CRUD events."""

    __tablename__ = "user_activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # No FK constraints — users/organizations live in identity_db
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("idx_activity_logs_action", "action"),
        Index("idx_activity_logs_created", "created_at"),
    )

    def __repr__(self):
        return f"<UserActivityLog(id={self.id}, user_id={self.user_id}, action='{self.action}')>"


class AdminAuditLog(Base):
    """Tracks admin actions: who changed what, when."""

    __tablename__ = "admin_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # No FK constraint — users table lives in identity_db
    admin_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(UUID(as_uuid=True), nullable=False)
    changes = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("idx_audit_logs_target", "target_type", "target_id"),
        Index("idx_audit_logs_created", "created_at"),
    )

    def __repr__(self):
        return f"<AdminAuditLog(id={self.id}, admin={self.admin_user_id}, action='{self.action}')>"


class AdminNotification(Base):
    """In-app notifications for system admins."""

    __tablename__ = "admin_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # No FK constraint — users table lives in identity_db
    recipient_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index(
            "idx_notifications_unread",
            "recipient_user_id",
            "is_read",
            postgresql_where=text("is_read = FALSE"),
        ),
        Index("idx_notifications_created", "created_at"),
    )

    def __repr__(self):
        return f"<AdminNotification(id={self.id}, recipient={self.recipient_user_id}, type='{self.notification_type}')>"


class FeatureFlag(Base):
    """Per-organization feature flags."""

    __tablename__ = "feature_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # No FK constraint — organizations table lives in identity_db
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    feature_key = Column(String(100), nullable=False)
    is_enabled = Column(Boolean, default=False)
    config = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "feature_key", name="unique_org_feature"
        ),
    )

    def __repr__(self):
        return f"<FeatureFlag(id={self.id}, org={self.organization_id}, key='{self.feature_key}')>"
