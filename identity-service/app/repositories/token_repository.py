"""Token repository for database operations"""

from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.token import RefreshToken


class TokenRepository:
    """Repository for refresh token database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_refresh_token(self, token_data: dict) -> RefreshToken:
        """
        Create a new refresh token.

        Args:
            token_data: Dictionary containing token data

        Returns:
            Created RefreshToken object
        """
        token = RefreshToken(**token_data)
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_refresh_token(self, token_hash: str) -> Optional[RefreshToken]:
        """
        Get refresh token by hash.

        Args:
            token_hash: Hashed token string

        Returns:
            RefreshToken object or None if not found
        """
        return self.db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None)
        ).first()

    def revoke_refresh_token(
        self,
        token: RefreshToken,
        reason: str = "user_logout"
    ) -> RefreshToken:
        """
        Revoke a refresh token.

        Args:
            token: RefreshToken object to revoke
            reason: Reason for revocation

        Returns:
            Updated RefreshToken object
        """
        token.revoked_at = datetime.now(timezone.utc)
        token.revoked_reason = reason
        self.db.commit()
        self.db.refresh(token)
        return token

    def update_last_used(self, token: RefreshToken) -> RefreshToken:
        """
        Update the last_used_at timestamp.

        Args:
            token: RefreshToken object to update

        Returns:
            Updated RefreshToken object
        """
        token.last_used_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(token)
        return token

    def delete_expired_tokens(self) -> int:
        """
        Delete all expired refresh tokens.

        Returns:
            Number of tokens deleted
        """
        count = self.db.query(RefreshToken).filter(
            RefreshToken.expires_at < datetime.now(timezone.utc)
        ).delete()
        self.db.commit()
        return count

    def revoke_all_user_tokens(self, user_id: UUID, reason: str = "security") -> int:
        """
        Revoke all refresh tokens for a user.

        Args:
            user_id: User UUID
            reason: Reason for revocation

        Returns:
            Number of tokens revoked
        """
        count = self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None)
        ).update({
            "revoked_at": datetime.now(timezone.utc),
            "revoked_reason": reason
        })
        self.db.commit()
        return count
