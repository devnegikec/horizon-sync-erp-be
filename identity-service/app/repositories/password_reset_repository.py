"""Password reset repository for database operations"""

from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
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
    
    def get_password_reset(self, token_hash: str) -> Optional[PasswordReset]:
        """
        Get password reset token by hash.
        
        Args:
            token_hash: Hashed token string
            
        Returns:
            PasswordReset object or None if not found
        """
        return self.db.query(PasswordReset).filter(
            PasswordReset.token_hash == token_hash,
            PasswordReset.used_at.is_(None),
            PasswordReset.expires_at > datetime.now(timezone.utc)
        ).first()
    
    def mark_as_used(self, reset: PasswordReset) -> PasswordReset:
        """
        Mark a password reset token as used.
        
        Args:
            reset: PasswordReset object to mark as used
            
        Returns:
            Updated PasswordReset object
        """
        reset.used_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(reset)
        return reset
    
    def delete_expired_tokens(self) -> int:
        """
        Delete all expired password reset tokens.
        
        Returns:
            Number of tokens deleted
        """
        count = self.db.query(PasswordReset).filter(
            PasswordReset.expires_at < datetime.now(timezone.utc)
        ).delete()
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
        count = self.db.query(PasswordReset).filter(
            PasswordReset.user_id == user_id,
            PasswordReset.used_at.is_(None)
        ).update({"used_at": datetime.now(timezone.utc)})
        self.db.commit()
        return count
