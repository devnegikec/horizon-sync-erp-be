"""Authentication service with business logic"""

import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    verify_password,
    validate_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token
)
from app.core.exceptions import (
    AuthenticationError,
    AccountLockedException,
    DuplicateEmailException,
    PasswordValidationException,
    InvalidTokenException,
    TokenExpiredException,
    UserNotFoundException
)
from app.models.user import User
from app.models.base import UserStatus, UserType
from app.repositories.user_repository import UserRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.config import settings


class AuthService:
    """Service for authentication operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = TokenRepository(db)
        self.password_reset_repo = PasswordResetRepository(db)
    
    def register_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        device_info: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[User, str, str]:
        """
        Register a new user.
        
        Args:
            email: User email
            password: Plain text password
            first_name: User first name
            last_name: User last name
            phone: Optional phone number
            device_info: Optional device information
            ip_address: Optional IP address
            user_agent: Optional user agent string
            
        Returns:
            Tuple of (User, access_token, refresh_token)
            
        Raises:
            DuplicateEmailException: If email already exists
            PasswordValidationException: If password is weak
        """
        # Check if email already exists
        if self.user_repo.email_exists(email):
            raise DuplicateEmailException(f"Email {email} is already registered")
        
        # Validate password strength
        is_valid, message = validate_password(password)
        if not is_valid:
            raise PasswordValidationException(message)
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create user
        user_data = {
            "email": email,
            "password_hash": password_hash,
            "first_name": first_name,
            "last_name": last_name,
            "display_name": f"{first_name} {last_name}",
            "phone": phone,
            "user_type": UserType.USER,
            "status": UserStatus.PENDING,
            "email_verified": False,
            "is_active": True
        }
        
        user = self.user_repo.create_user(user_data)
        
        # Generate tokens
        access_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "user_type": user.user_type.value
        })
        
        refresh_token = create_refresh_token({
            "sub": str(user.id),
            "token_family": str(uuid.uuid4())
        })
        
        # Store refresh token
        self._store_refresh_token(
            user.id,
            refresh_token,
            device_info,
            ip_address,
            user_agent
        )
        
        return user, access_token, refresh_token
    
    def login_user(
        self,
        email: str,
        password: str,
        device_info: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[User, str, str]:
        """
        Authenticate user and generate tokens.
        
        Args:
            email: User email
            password: Plain text password
            device_info: Optional device information
            ip_address: Optional IP address
            user_agent: Optional user agent string
            
        Returns:
            Tuple of (User, access_token, refresh_token)
            
        Raises:
            AuthenticationError: If credentials are invalid
            AccountLockedException: If account is locked
        """
        # Get user by email
        user = self.user_repo.get_user_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")
        
        # Check if account is locked
        if self._is_account_locked(user):
            raise AccountLockedException(
                f"Account is locked until {user.locked_until}. "
                "Too many failed login attempts."
            )
        
        # Verify password
        if not verify_password(password, user.password_hash):
            self._handle_failed_login(user)
            raise AuthenticationError("Invalid email or password")
        
        # Check if user is active
        if not user.is_active or user.status == UserStatus.SUSPENDED:
            raise AuthenticationError("Account is inactive or suspended")
        
        # Reset failed attempts on successful login
        self.user_repo.update_user(user, {
            "failed_login_attempts": 0,
            "locked_until": None,
            "last_login_at": datetime.now(timezone.utc),
            "last_login_ip": ip_address
        })
        
        # Generate tokens
        access_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "user_type": user.user_type.value
        })
        
        refresh_token = create_refresh_token({
            "sub": str(user.id),
            "token_family": str(uuid.uuid4())
        })
        
        # Store refresh token
        self._store_refresh_token(
            user.id,
            refresh_token,
            device_info,
            ip_address,
            user_agent
        )
        
        return user, access_token, refresh_token
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Generate new access token from refresh token.
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            New access token
            
        Raises:
            InvalidTokenException: If token is invalid
            TokenExpiredException: If token is expired
            UserNotFoundException: If user not found
        """
        # Decode refresh token
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise InvalidTokenException("Invalid refresh token")
        
        # Check if token is expired
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise TokenExpiredException("Refresh token has expired")
        
        # Get token from database
        token_hash_value = hash_token(refresh_token)
        db_token = self.token_repo.get_refresh_token(token_hash_value)
        
        if not db_token:
            raise InvalidTokenException("Refresh token not found or has been revoked")
        
        # Check if token is expired in database
        if db_token.expires_at < datetime.now(timezone.utc):
            raise TokenExpiredException("Refresh token has expired")
        
        # Get user
        user = self.user_repo.get_user_by_id(db_token.user_id)
        if not user:
            raise UserNotFoundException("User not found")
        
        # Update last used timestamp
        self.token_repo.update_last_used(db_token)
        
        # Generate new access token
        access_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "user_type": user.user_type.value
        })
        
        return access_token
    
    def logout_user(self, refresh_token: str) -> bool:
        """
        Logout user by revoking refresh token.
        
        Args:
            refresh_token: Refresh token to revoke
            
        Returns:
            True if successful
            
        Raises:
            InvalidTokenException: If token not found
        """
        token_hash_value = hash_token(refresh_token)
        db_token = self.token_repo.get_refresh_token(token_hash_value)
        
        if not db_token:
            raise InvalidTokenException("Refresh token not found")
        
        self.token_repo.revoke_refresh_token(db_token, reason="user_logout")
        return True
    
    def _is_account_locked(self, user: User) -> bool:
        """Check if account is currently locked"""
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            return True
        
        # Unlock account if lock period has expired
        if user.locked_until and user.locked_until <= datetime.now(timezone.utc):
            self.user_repo.update_user(user, {
                "locked_until": None,
                "failed_login_attempts": 0,
                "status": UserStatus.ACTIVE
            })
        
        return False
    
    def _handle_failed_login(self, user: User):
        """Handle failed login attempt"""
        failed_attempts = user.failed_login_attempts + 1
        update_data = {"failed_login_attempts": failed_attempts}
        
        # Lock account after 5 failed attempts
        if failed_attempts >= 5:
            update_data["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=30)
            update_data["status"] = UserStatus.SUSPENDED
        
        self.user_repo.update_user(user, update_data)
    
    def _store_refresh_token(
        self,
        user_id: uuid.UUID,
        refresh_token: str,
        device_info: Optional[dict],
        ip_address: Optional[str],
        user_agent: Optional[str]
    ):
        """Store refresh token in database"""
        token_hash_value = hash_token(refresh_token)
        payload = decode_token(refresh_token)
        
        token_data = {
            "user_id": user_id,
            "token_hash": token_hash_value,
            "token_family": payload.get("token_family"),
            "expires_at": datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc),
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        
        if device_info:
            token_data.update({
                "device_name": device_info.get("device_name"),
                "device_type": device_info.get("device_type"),
                "os_info": device_info.get("os_info"),
                "browser_info": device_info.get("browser_info")
            })
        
        self.token_repo.create_refresh_token(token_data)
    
    def forgot_password(
        self,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        Generate password reset token for user.
        
        Args:
            email: User email
            ip_address: Optional IP address
            user_agent: Optional user agent string
            
        Returns:
            Password reset token (plain text)
            
        Raises:
            UserNotFoundException: If user not found (silently handled for security)
        """
        # Get user by email
        user = self.user_repo.get_user_by_email(email)
        
        # For security, don't reveal if email exists or not
        # Always return success, but only create token if user exists
        if not user:
            # Return a fake token to prevent email enumeration
            return secrets.token_urlsafe(32)
        
        # Revoke any existing unused tokens for this user
        self.password_reset_repo.revoke_user_tokens(user.id)
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        token_hash_value = hash_token(reset_token)
        
        # Store reset token
        reset_data = {
            "user_id": user.id,
            "token_hash": token_hash_value,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=settings.password_reset_token_expire_hours),
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        
        self.password_reset_repo.create_password_reset(reset_data)
        
        return reset_token
    
    def reset_password(
        self,
        token: str,
        new_password: str
    ) -> bool:
        """
        Reset user password using reset token.
        
        Args:
            token: Password reset token
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            InvalidTokenException: If token is invalid or expired
            PasswordValidationException: If password is weak
            UserNotFoundException: If user not found
        """
        # Validate new password
        is_valid, message = validate_password(new_password)
        if not is_valid:
            raise PasswordValidationException(message)
        
        # Get reset token from database
        token_hash_value = hash_token(token)
        reset = self.password_reset_repo.get_password_reset(token_hash_value)
        
        if not reset:
            raise InvalidTokenException("Invalid or expired password reset token")
        
        # Get user
        user = self.user_repo.get_user_by_id(reset.user_id)
        if not user:
            raise UserNotFoundException("User not found")
        
        # Hash new password
        password_hash = hash_password(new_password)
        
        # Update user password
        self.user_repo.update_user(user, {
            "password_hash": password_hash,
            "failed_login_attempts": 0,
            "locked_until": None
        })
        
        # Mark token as used
        self.password_reset_repo.mark_as_used(reset)
        
        # Revoke all refresh tokens for security
        self.token_repo.revoke_all_user_tokens(user.id, reason="password_reset")
        
        return True
