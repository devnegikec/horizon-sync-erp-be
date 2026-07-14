"""OTP service — generate, send, and verify OTPs"""

import logging
import random
import string
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.repositories.otp_repository import OTPRepository

logger = logging.getLogger(__name__)

OTP_EXPIRE_MINUTES = 10
MAX_ATTEMPTS = 5


def _generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


class OTPService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OTPRepository(db)

    # ------------------------------------------------------------------
    # Send
    # ------------------------------------------------------------------

    def send_email_otp(self, email: str, ip_address: str | None = None) -> str:
        """
        Generate and 'send' an email OTP.
        In development the OTP is logged to the server console so the test
        team can grab it without needing a real SMTP server.
        Returns the plain OTP code (for logging; never expose in API response).
        """
        otp_code = _generate_otp()
        self._persist_otp("email", email, otp_code, ip_address)

        # Always log for test team visibility
        logger.info("=" * 50)
        logger.info("📧  EMAIL OTP GENERATED")
        logger.info(f"    Target  : {email}")
        logger.info(f"    OTP Code: {otp_code}")
        logger.info(f"    Expires : {OTP_EXPIRE_MINUTES} minutes")
        logger.info("=" * 50)

        # TODO: plug in real email sending here when ready
        # email_service.send_otp_email(email, otp_code)

        return otp_code

    def send_mobile_otp(self, mobile: str, ip_address: str | None = None) -> str:
        """
        Generate and 'send' a mobile OTP.
        Logged to server console for test team.
        """
        otp_code = _generate_otp()
        self._persist_otp("mobile", mobile, otp_code, ip_address)

        logger.info("=" * 50)
        logger.info("📱  MOBILE OTP GENERATED")
        logger.info(f"    Target  : {mobile}")
        logger.info(f"    OTP Code: {otp_code}")
        logger.info(f"    Expires : {OTP_EXPIRE_MINUTES} minutes")
        logger.info("=" * 50)

        # TODO: plug in real SMS/WhatsApp sending here when ready
        # sms_service.send_otp(mobile, otp_code)

        return otp_code

    # ------------------------------------------------------------------
    # Verify
    # ------------------------------------------------------------------

    def verify_otp(self, target: str, otp_type: str, otp_code: str) -> bool:
        """
        Verify an OTP for a given target (email or mobile).

        Raises:
            ValueError: with a user-friendly message on failure
        """
        record = self.repo.get_latest_active(target, otp_type)

        if not record:
            raise ValueError("OTP not found or has expired. Please request a new one.")

        if record.attempts >= MAX_ATTEMPTS:
            raise ValueError(
                "Too many incorrect attempts. Please request a new OTP."
            )

        if record.otp_code != otp_code:
            self.repo.increment_attempts(record)
            remaining = MAX_ATTEMPTS - record.attempts
            raise ValueError(
                f"Incorrect OTP. {remaining} attempt(s) remaining."
            )

        self.repo.mark_verified(record)

        logger.info("=" * 50)
        logger.info("✅  OTP VERIFIED")
        logger.info(f"    Target   : {target}")
        logger.info(f"    OTP Type : {otp_type}")
        logger.info("=" * 50)

        return True

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _persist_otp(
        self,
        otp_type: str,
        target: str,
        otp_code: str,
        ip_address: str | None,
    ) -> None:
        # Invalidate any previous active OTPs for this target
        self.repo.invalidate_previous(target, otp_type)

        self.repo.create(
            {
                "otp_type": otp_type,
                "target": target,
                "otp_code": otp_code,
                "expires_at": datetime.now(UTC) + timedelta(minutes=OTP_EXPIRE_MINUTES),
                "ip_address": ip_address,
            }
        )
