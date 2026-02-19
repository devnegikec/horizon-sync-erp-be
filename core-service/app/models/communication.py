"""Communication log model"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import (
    CommunicationChannel,
    CommunicationDocType,
    CommunicationStatus,
    RecipientType,
)
from app.models.types import JSONB, UUID


class CommunicationLog(Base):
    __tablename__ = "communication_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    doc_type = Column(
        Enum(
            CommunicationDocType,
            name="communicationdoctype",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        nullable=False,
    )
    doc_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    doc_no = Column(String(100), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    channel = Column(
        Enum(
            CommunicationChannel,
            name="communicationchannel",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        nullable=False,
    )
    recipient_type = Column(
        Enum(
            RecipientType,
            name="recipienttype",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        nullable=True,
    )
    recipient = Column(String(255), nullable=False)
    recipient_name = Column(String(255), nullable=True)
    sender_id = Column(UUID(as_uuid=True), nullable=False)
    sender_name = Column(String(255), nullable=True)
    sender_email = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=True)
    message = Column(Text, nullable=True)
    status = Column(
        Enum(
            CommunicationStatus,
            name="communicationstatus",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=CommunicationStatus.PENDING,
        nullable=False,
    )
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
