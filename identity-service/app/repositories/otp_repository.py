"""OTP verification repository"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.otp import OTPVerification


class OTPRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> OTPVerification:
        otp = OTPVerification(**data)
        self.db.add(otp)
        self.db.commit()
        self.db.refresh(otp)
        return otp

    def get_latest_active(self, target: str, otp_type: str) -> OTPVerification | None:
        """Get the most recent unverified, unexpired OTP for a target."""
        return (
            self.db.query(OTPVerification)
            .filter(
                OTPVerification.target == target,
                OTPVerification.otp_type == otp_type,
                OTPVerification.is_verified == False,  # noqa: E712
                OTPVerification.expires_at > datetime.now(UTC),
            )
            .order_by(OTPVerification.created_at.desc())
            .first()
        )

    def mark_verified(self, otp: OTPVerification) -> OTPVerification:
        otp.is_verified = True
        otp.verified_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(otp)
        return otp

    def increment_attempts(self, otp: OTPVerification) -> OTPVerification:
        otp.attempts += 1
        self.db.commit()
        self.db.refresh(otp)
        return otp

    def invalidate_previous(self, target: str, otp_type: str) -> None:
        """Expire all previous active OTPs for this target so only the latest is valid."""
        self.db.query(OTPVerification).filter(
            OTPVerification.target == target,
            OTPVerification.otp_type == otp_type,
            OTPVerification.is_verified == False,  # noqa: E712
        ).update({"expires_at": datetime.now(UTC)})
        self.db.commit()
