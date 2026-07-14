"""Reminder configuration and logging models for payment reminders

Task 1D-1: Models for reminder configuration, escalation, and audit logging
"""

import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import ARRAY, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class ReminderType(str, Enum):
    """Types of payment reminders"""
    MANUAL = "manual"
    AUTO = "auto"
    CONFIGURED = "configured"


class ReminderStage(str, Enum):
    """Stages in reminder escalation sequence"""
    FIRST_REMINDER = "first_reminder"      # 30 days overdue
    SECOND_REMINDER = "second_reminder"    # 60 days overdue
    FINAL_NOTICE = "final_notice"          # 90 days overdue
    DEACTIVATION_NOTICE = "deactivation_notice"  # Before deactivation


class ReminderStatus(str, Enum):
    """Status of reminder sending"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class ReminderConfig(Base):
    """Configuration for payment reminders per organization
    
    Task 1D-1: Stores reminder settings and escalation sequence
    """
    __tablename__ = "reminder_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True, unique=True)
    
    # Reminder type and settings
    reminder_type = Column(
        SQLEnum(ReminderType, values_callable=lambda x: [e.value for e in x]), 
        nullable=False, 
        default=ReminderType.AUTO
    )
    
    # Grace periods and frequencies (in days)
    grace_period_days = Column(Integer, nullable=False, default=30)
    first_reminder_days = Column(Integer, nullable=False, default=30)  # Days overdue for 1st reminder
    second_reminder_days = Column(Integer, nullable=False, default=60)  # Days overdue for 2nd reminder
    final_notice_days = Column(Integer, nullable=False, default=90)     # Days overdue for final notice
    auto_deactivate_days = Column(Integer, nullable=False, default=120) # Days overdue for deactivation
    
    # Reminder frequency settings
    reminder_frequency_days = Column(Integer, nullable=False, default=7)  # Days between reminders
    max_reminders_per_stage = Column(Integer, nullable=False, default=3)   # Max reminders per stage
    
    # Escalation sequence (array of reminder stages)
    escalation_sequence = Column(ARRAY(String), nullable=False, default=[
        ReminderStage.FIRST_REMINDER,
        ReminderStage.SECOND_REMINDER,
        ReminderStage.FINAL_NOTICE,
        ReminderStage.DEACTIVATION_NOTICE
    ])
    
    # Email template mappings (template names for each stage)
    first_reminder_template = Column(String(100), nullable=False, default="payment_reminder_first")
    second_reminder_template = Column(String(100), nullable=False, default="payment_reminder_second")
    final_notice_template = Column(String(100), nullable=False, default="payment_reminder_final")
    deactivation_notice_template = Column(String(100), nullable=False, default="payment_reminder_deactivation")
    
    # Settings
    is_enabled = Column(Boolean, nullable=False, default=True)
    auto_deactivate_enabled = Column(Boolean, nullable=False, default=True)
    send_copy_to_admin = Column(Boolean, nullable=False, default=True)
    
    # Additional configuration
    custom_settings = Column(JSONB, nullable=True, default={})
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), 
                       onupdate=lambda: datetime.now(UTC), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)

    def __repr__(self):
        return f"<ReminderConfig(id={self.id}, org={self.organization_id}, type={self.reminder_type})>"


class ReminderLog(Base):
    """Log of sent payment reminders for audit and tracking
    
    Task 1D-1: Tracks all reminder attempts and their outcomes
    """
    __tablename__ = "reminder_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    invoice_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    config_id = Column(UUID(as_uuid=True), nullable=True)  # Reference to ReminderConfig
    
    # Reminder details
    reminder_stage = Column(
        SQLEnum(ReminderStage, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    reminder_type = Column(
        SQLEnum(ReminderType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    
    # Sending details
    recipient_email = Column(String(255), nullable=False)
    recipient_name = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=False)
    template_used = Column(String(100), nullable=True)
    
    # Status and timing
    status = Column(
        SQLEnum(ReminderStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ReminderStatus.PENDING
    )
    sent_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    
    # Invoice context at time of sending
    invoice_amount = Column(String(20), nullable=True)  # Store as string to preserve formatting
    outstanding_amount = Column(String(20), nullable=True)
    days_overdue = Column(Integer, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    
    # Delivery tracking
    email_response = Column(JSONB, nullable=True)  # Store email service response
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    
    # Escalation tracking
    stage_attempt_number = Column(Integer, nullable=False, default=1)  # Which attempt in this stage
    next_reminder_due = Column(DateTime(timezone=True), nullable=True)
    
    # Additional context
    triggered_by = Column(String(50), nullable=False)  # 'manual', 'automated', 'batch'
    user_id = Column(UUID(as_uuid=True), nullable=True)  # User who triggered (if manual)
    batch_id = Column(UUID(as_uuid=True), nullable=True)  # For batch processing
    additional_data = Column(JSONB, nullable=True, default={})
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC),
                       onupdate=lambda: datetime.now(UTC), nullable=False)

    def __repr__(self):
        return f"<ReminderLog(id={self.id}, invoice={self.invoice_id}, stage={self.reminder_stage}, status={self.status})>"