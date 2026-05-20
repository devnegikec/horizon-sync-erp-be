"""Password reset repository for database operations"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.password_reset import PasswordReset


class PasswordResetRepository:
    """Repository for password reset database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_password_reset(self, reset_data: dict) -> PasswordReset:
        """
        Create a new password reset token.

        Args:
            reset_data: Dictionary containing reset token data

        Returns:
            Created PasswordReset object
        """
        reset = PasswordReset(**reset_data)
        self.db.add(reset)
        self.db.commit()
        self.db.refresh(reset)
        return reset

    def get_password_reset(self, token_hash: str) -> PasswordReset | None:
        """
        Get password reset token by hash.

        Args:
            token_hash: Hashed token string

        Returns:
            PasswordReset object or None if not found
        """
        return (
            self.db.query(PasswordReset)
            .filter(
                PasswordReset.token_hash == token_hash,
                PasswordReset.used_at.is_(None),
                PasswordReset.expires_at > datetime.now(UTC),
            )
            .first()
        )

    def is_token_valid(self, token_hash: str) -> bool:
        """Return True if the token exists, is not yet used, and not expired."""
        return self.get_password_reset(token_hash) is not None

    def get_latest_active_for_user(self, user_id: UUID) -> PasswordReset | None:
        """
        Return the most recently-created unused, unexpired reset token for a user,
        if any. Used to enforce a cooldown between forgot-password requests.
        """
        return (
            self.db.query(PasswordReset)
            .filter(
                PasswordReset.user_id == user_id,
                PasswordReset.used_at.is_(None),
                PasswordReset.expires_at > datetime.now(UTC),
            )
            .order_by(PasswordReset.created_at.desc())
            .first()
        )

    def mark_as_used(self, reset: PasswordReset) -> PasswordReset:
        """
        Mark a password reset token as used.

        Args:
            reset: PasswordReset object to mark as used

        Returns:
            Updated PasswordReset object
        """
        reset.used_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(reset)
        return reset

    def delete_expired_tokens(self) -> int:
        """
        Delete all expired password reset tokens.

        Returns:
            Number of tokens deleted
        """
        count = (
            self.db.query(PasswordReset)
            .filter(PasswordReset.expires_at < datetime.now(UTC))
            .delete()
        )
        self.db.commit()
        return count

    def revoke_user_tokens(self, user_id: UUID) -> int:
        """
        Revoke all unused password reset tokens for a user.

        Args:
            user_id: User UUID

        Returns:
            Number of tokens revoked
        """
        count = (
            self.db.query(PasswordReset)
            .filter(PasswordReset.user_id == user_id, PasswordReset.used_at.is_(None))
            .update({"used_at": datetime.now(UTC)})
        )
        self.db.commit()
        return count
