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
from app.models.role import Permission, Role, RolePermission
from app.models.user import User
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository


class AuthService:
    """Service for authentication operations"""

    # Permission codes required by the warehouse_work_user role.
    # Must stay in sync with workers.py and identity_role_service.py.
    _WORKER_REQUIRED_PERMISSIONS = [
        "warehouse.read",
        "wms.scan",
        "receiving_slip.create",
        "receiving_slip.read",
        "receiving_slip.update",
        "inbound_exception.read",
        "inbound_exception.create",
        "pick_list.read",
        "pick_list.update",
        "stock_entry.create",
        "stock_entry.read",
    ]

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

        # Warehouse workers must use QR or the worker app, never the web portal.
        if user.user_type == UserType.WAREHOUSE_WORKER:
            raise AuthenticationError(
                "Warehouse workers must log in via the worker app (QR code or username/password), not the web portal"
            )

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

    def login_by_qr_code(
        self,
        qr_code: str,
        device_info: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str]:
        """
        Authenticate a warehouse worker via QR code scan.

        Looks up the user by their unique QR code, validates they are an active
        warehouse worker, and returns JWT tokens. No password required.

        Args:
            qr_code: The worker's unique QR code string (from QR scan)
            device_info: Optional device information
            ip_address: Optional IP address
            user_agent: Optional user agent string

        Returns:
            Tuple of (User, access_token, refresh_token)

        Raises:
            AuthenticationError: If QR code is invalid or worker is not active
        """
        # Look up user by QR code (single source of truth: users.qr_code)
        user = self.user_repo.get_user_by_qr_code(qr_code)
        if not user:
            raise AuthenticationError("Invalid QR code")

        # Verify user is a warehouse worker
        if user.user_type != UserType.WAREHOUSE_WORKER:
            raise AuthenticationError(
                "QR code login is only available for warehouse workers"
            )

        # Check if user is active
        if not user.is_active or user.status == UserStatus.SUSPENDED:
            raise AuthenticationError("Worker account is inactive or suspended")

        # --- Ensure the worker's role has all required permissions ---
        # (patches roles created before the seed-data fix or auto-seeded without perms)
        self._ensure_worker_permissions(user)

        # Update login tracking
        self.user_repo.update_user(
            user,
            {
                "last_login_at": datetime.now(UTC),
                "last_login_ip": ip_address,
            },
        )

        # Generate tokens with worker-specific TTL
        worker_ttl_hours = getattr(settings, "worker_token_expire_hours", 20)
        access_token_expires = timedelta(hours=worker_ttl_hours)
        refresh_token_expires = timedelta(hours=worker_ttl_hours * 2)

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

    def login_worker(
        self,
        login_username: str,
        password: str,
        device_info: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str]:
        """Authenticate a warehouse worker by username + password.

        Fallback for when QR login is unavailable (mobile/device only).
        The worker must have a managed `login_username` + password.
        """
        user = (
            self.db.query(User)
            .filter(User.login_username == login_username)
            .first()
        )
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password")

        if user.user_type != UserType.WAREHOUSE_WORKER:
            raise AuthenticationError(
                "Username/password login is only available for warehouse workers"
            )

        if not user.is_active or user.status == UserStatus.SUSPENDED:
            raise AuthenticationError("Worker account is inactive or suspended")

        self._ensure_worker_permissions(user)
        self.user_repo.update_user(
            user,
            {
                "last_login_at": datetime.now(UTC),
                "last_login_ip": ip_address,
            },
        )

        worker_ttl_hours = getattr(settings, "worker_token_expire_hours", 20)
        access_token_expires = timedelta(hours=worker_ttl_hours)
        refresh_token_expires = timedelta(hours=worker_ttl_hours * 2)

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
        self._store_refresh_token(
            user.id, refresh_token, device_info, ip_address, user_agent
        )
        return user, access_token, refresh_token

    def _ensure_worker_permissions(self, user: User) -> None:
        """Ensure the warehouse_work_user role has all required permissions.

        Patches roles that were created before the seed-data fix or
        auto-seeded by core-service without permissions.
        Idempotent — skips permissions already assigned.
        """
        import logging

        logger = logging.getLogger(__name__)

        # Find the worker's warehouse_work_user role
        ww_role = (
            self.db.query(Role)
            .filter(
                Role.code == "warehouse_work_user",
                Role.is_active == True,  # noqa: E712
            )
            .first()
        )
        if not ww_role:
            logger.warning(
                "warehouse_work_user role not found — cannot patch permissions"
            )
            return

        # Fetch all required Permission objects
        required_perms = (
            self.db.query(Permission)
            .filter(
                Permission.code.in_(self._WORKER_REQUIRED_PERMISSIONS),
                Permission.is_active == True,  # noqa: E712
            )
            .all()
        )

        found_codes = {p.code for p in required_perms}
        missing_codes = set(self._WORKER_REQUIRED_PERMISSIONS) - found_codes
        if missing_codes:
            logger.warning(
                "Permissions not found in DB: %s — workers may be incomplete",
                ", ".join(sorted(missing_codes)),
            )

        if not required_perms:
            return

        # Fetch already-assigned permission IDs
        existing_ids = set(
            row[0]
            for row in self.db.query(RolePermission.permission_id)
            .filter(RolePermission.role_id == ww_role.id)
            .all()
        )

        # Assign missing permissions
        assigned = 0
        for perm in required_perms:
            if perm.id not in existing_ids:
                self.db.add(RolePermission(role_id=ww_role.id, permission_id=perm.id))
                assigned += 1

        if assigned:
            self.db.flush()
            logger.info(
                "QR login: auto-assigned %d missing permissions to warehouse_work_user role %s",
                assigned,
                ww_role.id,
            )

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
        failed_attempts = (user.failed_login_attempts or 0) + 1
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
    ) -> tuple[str | None, int]:
        """
        Generate (or skip) a password reset token for the given email.

        To prevent email enumeration, this method behaves identically for known
        and unknown emails from the caller's perspective: it always returns a
        ``(token, retry_after_seconds)`` tuple where ``token`` may be ``None``
        when no email should be sent (cooldown active or user not found).

        Behaviour:

        * Unknown email → returns ``(None, COOLDOWN)`` so the endpoint can
          still respond with the generic "if the email exists" message and a
          consistent cooldown hint.
        * Known email with an unused, unexpired token issued within the
          cooldown window → returns ``(None, remaining_seconds)``; **no new
          token is created and no email should be sent**. The user must use
          (or wait for the cooldown on) the previously-emailed link.
        * Otherwise → revokes any prior tokens, creates a fresh one, and
          returns ``(token, COOLDOWN)``.

        Args:
            email: User email
            ip_address: Optional IP address
            user_agent: Optional user agent string

        Returns:
            Tuple of ``(reset_token_or_None, retry_after_seconds)``.
        """
        cooldown = settings.password_reset_cooldown_seconds

        user = self.user_repo.get_user_by_email(email)
        if not user:
            # Return no token (so no email is sent) but still surface a
            # cooldown to keep the response timing/content uniform.
            return None, cooldown

        # If a still-valid token was issued recently, do nothing — the user
        # already has an email with a working link in their inbox.
        latest = self.password_reset_repo.get_latest_active_for_user(user.id)
        if latest is not None:
            created = latest.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            elapsed = (datetime.now(UTC) - created).total_seconds()
            if elapsed < cooldown:
                remaining = max(1, int(cooldown - elapsed))
                return None, remaining

        # Cooldown elapsed (or no prior token): rotate.
        self.password_reset_repo.revoke_user_tokens(user.id)

        reset_token = secrets.token_urlsafe(32)
        token_hash_value = hash_token(reset_token)
        reset_data = {
            "user_id": user.id,
            "token_hash": token_hash_value,
            "expires_at": datetime.now(UTC)
            + timedelta(hours=settings.password_reset_token_expire_hours),
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
        self.password_reset_repo.create_password_reset(reset_data)

        return reset_token, cooldown

    def is_password_reset_token_valid(self, token: str) -> bool:
        """Return True if `token` is a valid (unused, unexpired) password reset token."""
        if not token:
            return False
        return self.password_reset_repo.is_token_valid(hash_token(token))

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

        # Update user password.
        # Also clear any prior lockout/suspension that resulted from failed
        # login attempts — otherwise the user resets their password
        # successfully but is still blocked at login by the suspended-status
        # check, which is then surfaced as a misleading
        # "Invalid email or password" error.
        update_data: dict = {
            "password_hash": password_hash,
            "failed_login_attempts": 0,
            "locked_until": None,
        }
        if user.status == UserStatus.SUSPENDED:
            update_data["status"] = UserStatus.ACTIVE
        self.user_repo.update_user(user, update_data)

        # Mark token as used
        self.password_reset_repo.mark_as_used(reset)

        # Revoke all refresh tokens for security
        self.token_repo.revoke_all_user_tokens(user.id, reason="password_reset")

        return True
