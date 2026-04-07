"""User related database models"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import UserStatus, UserType


class User(Base):
    """User model"""

    __tablename__ = "users"
    __audited__ = True
    __audit_exclude__ = {"password_hash"}

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    display_name = Column(String(200))
    phone = Column(String(20))
    avatar_url = Column(String(500))

    # User type and status
    user_type = Column(
        SQLEnum(UserType, values_callable=lambda x: [e.value for e in x]),
        default=UserType.USER,
        nullable=False,
    )
    status = Column(
        SQLEnum(UserStatus, values_callable=lambda x: [e.value for e in x]),
        default=UserStatus.PENDING,
        nullable=False,
    )
    is_active = Column(Boolean, default=True, nullable=False)

    # Email verification
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime(timezone=True))

    # MFA (Multi-Factor Authentication)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255))
    mfa_backup_codes = Column(JSON)

    # Login tracking
    last_login_at = Column(DateTime(timezone=True))
    last_login_ip = Column(String(45))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True))

    # User preferences
    preferences = Column(JSON, default={})
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")

    # Metadata
    extra_data = Column(JSON, default={})
    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    email_verifications = relationship(
        "EmailVerification", back_populates="user", cascade="all, delete-orphan"
    )
    user_organization_roles = relationship(
        "UserOrganizationRole",
        back_populates="user",
        foreign_keys="UserOrganizationRole.user_id",
        cascade="all, delete-orphan",
    )


class EmailVerification(Base):
    """Email verification token model"""

    __tablename__ = "email_verifications"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True))
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="email_verifications")
