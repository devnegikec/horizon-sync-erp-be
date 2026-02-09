"""Authentication service with business logic"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import (
    AccountLockedException,
    AuthenticationError,
    DuplicateEmailException,
    InvalidTokenException,
    PasswordValidationException,
    TokenExpiredException,
    UserNotFoundException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    validate_password,
    verify_password,
)
from app.models.base import UserStatus, UserType
from app.models.user import User
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository


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
        phone: str | None = None,
        device_info: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str]:
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
            "is_active": True,
        }

        user = self.user_repo.create_user(user_data)

        # Generate tokens
        access_token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "user_type": user.user_type.value,
            }
        )

        refresh_token = create_refresh_token(
            {"sub": str(user.id), "token_family": str(uuid.uuid4())}
        )

        # Store refresh token
        self._store_refresh_token(
            user.id, refresh_token, device_info, ip_address, user_agent
        )

        return user, access_token, refresh_token

    def login_user(
        self,
        email: str,
        password: str,
        remember_me: bool = False,
        device_info: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str]:
        """
        Authenticate user and generate tokens.

        Args:
            email: User email
            password: Plain text password
            remember_me: Whether to extend token expiration for "Remember Me"
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
        self.user_repo.update_user(
            user,
            {
                "failed_login_attempts": 0,
                "locked_until": None,
                "last_login_at": datetime.now(UTC),
                "last_login_ip": ip_address,
            },
        )

        # Generate tokens with appropriate expiration based on remember_me
        if remember_me:
            # Extended expiration for "Remember Me"
            access_token_expires = timedelta(
                days=settings.remember_me_access_token_expire_days
            )
            refresh_token_expires = timedelta(
                days=settings.remember_me_refresh_token_expire_days
            )
        else:
            # Standard expiration
            access_token_expires = timedelta(
                minutes=settings.access_token_expire_minutes
            )
            refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)

        access_token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "user_type": user.user_type.value,
            },
            expires_delta=access_token_expires,
        )

        refresh_token = create_refresh_token(
            {"sub": str(user.id), "token_family": str(uuid.uuid4())},
            expires_delta=refresh_token_expires,
        )

        # Store refresh token
        self._store_refresh_token(
            user.id, refresh_token, device_info, ip_address, user_agent
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
        if exp and datetime.fromtimestamp(exp, tz=UTC) < datetime.now(UTC):
            raise TokenExpiredException("Refresh token has expired")

        # Get token from database
        token_hash_value = hash_token(refresh_token)
        db_token = self.token_repo.get_refresh_token(token_hash_value)

        if not db_token:
            raise InvalidTokenException("Refresh token not found or has been revoked")

        # Check if token is expired in database
        expires_at = db_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if expires_at < datetime.now(UTC):
            raise TokenExpiredException("Refresh token has expired")

        # Get user
        user = self.user_repo.get_user_by_id(db_token.user_id)
        if not user:
            raise UserNotFoundException("User not found")

        # Update last used timestamp
        self.token_repo.update_last_used(db_token)

        # Generate new access token
        access_token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "user_type": user.user_type.value,
            }
        )

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
        if not user.locked_until:
            return False

        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=UTC)

        if locked_until > datetime.now(UTC):
            return True

        # Unlock account if lock period has expired
        if locked_until <= datetime.now(UTC):
            self.user_repo.update_user(
                user,
                {
                    "locked_until": None,
                    "failed_login_attempts": 0,
                    "status": UserStatus.ACTIVE,
                },
            )

        return False

    def _handle_failed_login(self, user: User):
        """Handle failed login attempt"""
        failed_attempts = user.failed_login_attempts + 1
        update_data = {"failed_login_attempts": failed_attempts}

        # Lock account after 5 failed attempts
        if failed_attempts >= 5:
            update_data["locked_until"] = datetime.now(UTC) + timedelta(minutes=30)
            update_data["status"] = UserStatus.SUSPENDED

        self.user_repo.update_user(user, update_data)

    def _store_refresh_token(
        self,
        user_id: uuid.UUID,
        refresh_token: str,
        device_info: dict | None,
        ip_address: str | None,
        user_agent: str | None,
    ):
        """Store refresh token in database"""
        token_hash_value = hash_token(refresh_token)
        payload = decode_token(refresh_token)

        token_data = {
            "user_id": user_id,
            "token_hash": token_hash_value,
            "token_family": payload.get("token_family"),
            "expires_at": datetime.fromtimestamp(payload.get("exp"), tz=UTC),
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        if device_info:
            token_data.update(
                {
                    "device_name": device_info.get("device_name"),
                    "device_type": device_info.get("device_type"),
                    "os_info": device_info.get("os_info"),
                    "browser_info": device_info.get("browser_info"),
                }
            )

        self.token_repo.create_refresh_token(token_data)

    def forgot_password(
        self,
        email: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
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
            "expires_at": datetime.now(UTC)
            + timedelta(hours=settings.password_reset_token_expire_hours),
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        self.password_reset_repo.create_password_reset(reset_data)

        return reset_token

    def reset_password(self, token: str, new_password: str) -> bool:
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
        self.user_repo.update_user(
            user,
            {
                "password_hash": password_hash,
                "failed_login_attempts": 0,
                "locked_until": None,
            },
        )

        # Mark token as used
        self.password_reset_repo.mark_as_used(reset)

        # Revoke all refresh tokens for security
        self.token_repo.revoke_all_user_tokens(user.id, reason="password_reset")

        return True
