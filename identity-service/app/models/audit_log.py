"""Audit log related database models"""

import uuid
from datetime import datetime
import enum

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    String,
    Uuid,
)
from sqlalchemy import Enum as SQLEnum

from app.database import Base


class AuditActionType(str, enum.Enum):
    """Audit action type enumeration"""
    
    ASSIGN = "assign"
    UPDATE = "update"
    REVOKE = "revoke"
    ACCESS_GRANT = "access_grant"
    ACCESS_REVOKE = "access_revoke"


class SystemAdminAuditLog(Base):
    """System admin audit log model for tracking administrative actions"""
    
    __tablename__ = "system_admin_audit_logs"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    action_id = Column(String(255), nullable=False, index=True)  # Unique identifier for the action
    
    # Action details
    action_type = Column(
        SQLEnum(AuditActionType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    
    # Admin user who performed the action
    admin_user_id = Column(Uuid, nullable=False, index=True)
    admin_username = Column(String(255), nullable=False)
    
    # Target user (if applicable)
    target_user_id = Column(Uuid, nullable=True, index=True)
    target_username = Column(String(255), nullable=True)
    
    # Target organization (if applicable)  
    target_organization_id = Column(Uuid, nullable=True, index=True)
    target_organization_name = Column(String(255), nullable=True)
    
    # Action details
    changes_made = Column(JSON, nullable=False, default={})  # Details of what changed
    performed_by = Column(String(255), nullable=False)  # Full name of admin user
    notes = Column(String(1000), nullable=True)  # Optional notes about the action
    
    # Timestamps
    performed_date = Column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        nullable=False,
        index=True
    )
    created_at = Column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )