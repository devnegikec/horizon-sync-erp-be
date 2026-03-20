"""Messaging module models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    template_name = Column(String(4000), nullable=False)
    channel = Column(String(10), nullable=False, index=True)  # sms|whatsapp|rcs|email
    template_type = Column(String(2), nullable=True)
    message = Column(Text, nullable=True)
    template_text = Column(Text, nullable=False)
    media_type = Column(String(3), nullable=True)
    interactive_type = Column(String(3), nullable=True)
    status = Column(String(40), default="Not Approved")
    sender_id = Column(String(6), nullable=True)
    cta_button1 = Column(String(20), nullable=True)
    cta_button2 = Column(String(20), nullable=True)
    qr_button1 = Column(String(20), nullable=True)
    qr_button2 = Column(String(20), nullable=True)
    qr_button3 = Column(String(20), nullable=True)
    entity_name = Column(String(50), nullable=True)
    dlt_principal_entity_id = Column(String(50), nullable=True)
    dlt_template_id = Column(String(50), nullable=True)
    mobtexting_template_id = Column(String(120), nullable=True)
    service_type = Column(String(1), default="T")  # T=transactional, P=promotional
    extra_data = Column(JSONB, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC),
                        onupdate=lambda: datetime.now(UTC))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<MessageTemplate(id={self.id}, name='{self.template_name}', channel='{self.channel}')>"


class BulkMessageJob(Base):
    __tablename__ = "bulk_message_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("campaign_tags.id"), nullable=True)
    message_type = Column(String(20), nullable=False)  # sms|whatsapp|rcs
    sender_id = Column(String(40), nullable=True)
    template_type = Column(String(100), nullable=True)
    media_type = Column(String(100), nullable=True)
    interactive_type = Column(String(100), nullable=True)
    template_name = Column(String(100), nullable=True)
    message_template = Column(Text, nullable=True)
    total_lead = Column(String(400), nullable=True)
    media_link = Column(Text, nullable=True)
    variable = Column(JSONB, nullable=True)
    coupon_type = Column(String(256), nullable=True)
    coupon_value = Column(Text, nullable=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    template_length = Column(String(30), nullable=True)
    used_credit = Column(String(30), nullable=True)
    status = Column(String(50), nullable=True, index=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(Date, default=lambda: datetime.now(UTC).date())

    sms_reports = relationship("SMSReport", back_populates="job")
    whatsapp_reports = relationship("WhatsAppReport", back_populates="job")
    rcs_reports = relationship("RCSReport", back_populates="job")


class ScheduledMessage(Base):
    __tablename__ = "scheduled_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("campaign_tags.id"), nullable=True)
    message_type = Column(String(20), nullable=False)
    template_name = Column(String(100), nullable=True)
    template_text = Column(String(400), nullable=True)
    variable = Column(JSONB, nullable=True)
    sender_id = Column(String(12), nullable=True)
    media_link = Column(Text, nullable=True)
    schedule = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(50), default="Pending")
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(Date, default=lambda: datetime.now(UTC).date())


class SMSReport(Base):
    __tablename__ = "sms_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("bulk_message_jobs.id"), nullable=True)
    tag = Column(String(50), nullable=True)
    msg_id = Column(String(150), nullable=True)
    sender_id = Column(String(12), nullable=True)
    recipient_number = Column(String(12), nullable=True, index=True)
    units = Column(String(50), nullable=True)
    credits = Column(String(250), nullable=True)
    location = Column(String(250), nullable=True)
    region = Column(String(250), nullable=True)
    provider = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)
    sent_date = Column(DateTime(timezone=True), nullable=True)
    deliver_date = Column(DateTime(timezone=True), nullable=True)
    submit_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(Date, default=lambda: datetime.now(UTC).date())

    job = relationship("BulkMessageJob", back_populates="sms_reports")


class WhatsAppReport(Base):
    __tablename__ = "whatsapp_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("bulk_message_jobs.id"), nullable=True)
    recipient_number = Column(String(12), nullable=True, index=True)
    sender_number = Column(String(12), nullable=True)
    operator = Column(String(50), nullable=True)
    circle = Column(String(50), nullable=True)
    conversation_id = Column(String(150), nullable=True)
    template_id = Column(String(150), nullable=True)
    conversation_type = Column(String(250), nullable=True)
    whatsapp_msg_id = Column(String(1000), nullable=True)
    guid = Column(String(250), unique=True, nullable=True)
    tag = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)
    reason_code = Column(String(50), nullable=True)
    sent_date = Column(DateTime(timezone=True), nullable=True)
    deliver_date = Column(DateTime(timezone=True), nullable=True)

    job = relationship("BulkMessageJob", back_populates="whatsapp_reports")


class RCSCredential(Base):
    __tablename__ = "rcs_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    config = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class RCSTemplate(Base):
    __tablename__ = "rcs_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(256), nullable=True)
    content = Column(JSONB, nullable=True)
    status = Column(String(40), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class RCSReport(Base):
    __tablename__ = "rcs_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("bulk_message_jobs.id"), nullable=True)
    recipient_number = Column(String(12), nullable=True)
    guid = Column(String(250), unique=True, nullable=True)
    status = Column(String(50), nullable=True)
    sent_date = Column(DateTime(timezone=True), nullable=True)
    deliver_date = Column(DateTime(timezone=True), nullable=True)

    job = relationship("BulkMessageJob", back_populates="rcs_reports")


class MessageCredit(Base):
    __tablename__ = "message_credits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    credit_type = Column(String(50), nullable=False)  # sms|whatsapp|rcs
    add_credit = Column(Integer, default=0)
    reduce_credit = Column(Integer, default=0)
    balance_credit = Column(Integer, default=0)
    payment_inr = Column(String(250), nullable=True)
    credit_value = Column(String(50), nullable=True)
    payment_detail = Column(String(400), nullable=True)
    transaction_date = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
