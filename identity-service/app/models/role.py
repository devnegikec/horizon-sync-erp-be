"""Role and Permission related database models"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum, Uuid, JSON
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import ResourceType, ActionType


class Role(Base):
    """Role model for RBAC"""
    __tablename__ = "roles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(Uuid, ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    description = Column(Text)

    # Role properties
    is_system = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    hierarchy_level = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="roles")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    user_organization_roles = relationship("UserOrganizationRole", back_populates="role")


class Permission(Base):
    """Permission model for RBAC"""
    __tablename__ = "permissions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # Permission details
    resource = Column(SQLEnum(ResourceType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    action = Column(SQLEnum(ActionType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    module = Column(String(50))
    category = Column(String(50))

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class RolePermission(Base):
    """Role-Permission mapping model"""
    __tablename__ = "role_permissions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    role_id = Column(Uuid, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True)
    permission_id = Column(Uuid, ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False, index=True)
    conditions = Column(JSON, default={})

    # Relationships
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")


class UserOrganizationRole(Base):
    """User-Organization-Role mapping model"""
    __tablename__ = "user_organization_roles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    organization_id = Column(Uuid, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    role_id = Column(Uuid, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True)

    # Role assignment details
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(String(20), default='active')

    # Invitation tracking
    invited_by_id = Column(Uuid, ForeignKey('users.id'))
    invited_at = Column(DateTime(timezone=True))
    joined_at = Column(DateTime(timezone=True))

    # Metadata
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships - specify foreign_keys to avoid ambiguity
    user = relationship("User", foreign_keys=[user_id], back_populates="user_organization_roles")
    organization = relationship("Organization", back_populates="user_organization_roles")
    role = relationship("Role", back_populates="user_organization_roles")
