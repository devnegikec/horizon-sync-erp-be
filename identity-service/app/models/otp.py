"""OTP verification model"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Uuid

from app.database import Base


class OTPVerification(Base):
    """OTP verification model for email and mobile OTP flows"""

    __tablename__ = "otp_verifications"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = Column(Uuid, nullable=True)

    # "email" or "mobile"
    otp_type = Column(String(20), nullable=False, index=True)

    # email address or phone number
    target = Column(String(255), nullable=False, index=True)

    otp_code = Column(String(10), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Track brute-force attempts
    attempts = Column(Integer, default=0, nullable=False)

    ip_address = Column(String(45), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
