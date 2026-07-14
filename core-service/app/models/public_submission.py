"""Public Submission model — stores all public/marketing form submissions"""

import uuid
from sqlalchemy import Column, String, Text, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class PublicSubmission(Base):
    __tablename__ = "public_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
                server_default=text("gen_random_uuid()"))
    submission_type = Column(String(30), nullable=False,
                             comment="contact_us | career | schedule_demo | newsletter | request_callback")
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    mobile = Column(String(20), nullable=True)
    company = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=True, comment="Full form data for type-specific fields")
    status = Column(String(20), server_default="new",
                    comment="new | acknowledged | processed")
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
