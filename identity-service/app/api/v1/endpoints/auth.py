"""Authentication API endpoints"""

from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
import io
from uuid import UUID

import qrcode
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.error_handler import handle_login_errors
from app.core.exceptions import (
    AccountLockedException,
    AuthenticationError,
    DuplicateEmailException,
    InvalidTokenException,
    PasswordValidationException,
    TokenExpiredException,
    UserNotFoundException,
)
from app.core.security import create_service_token, verify_client_secret
from app.database import get_db
from app.dependencies import (
    CurrentUser,
    get_client_ip,
    get_current_user,
    require_permission,
)
from app.models.base import UserType
from app.models.role import UserOrganizationRole
from app.models.service_credential import ServiceCredential
from app.schemas.auth import (
    ClientCredentialsRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginUserResponse,
    LogoutRequest,
    LogoutResponse,
    QRCodeLoginRequest,
    QRCodeLoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    ServiceTokenResponse,
    TokenResponse,
    VerifyResetTokenResponse,
)
from app.schemas.error import ErrorResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import AuthService
from app.services.email_service import EmailService

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        409: {"model": ErrorResponse, "description": "Email already exists"},
    },
)
async def register(
    user_data: UserCreate, request: Request, db: Session = Depends(get_db)
):
    """
    Register a new user.

    - **email**: Valid email address (unique)
    - **password**: Min 8 chars, must contain uppercase, lowercase, number, special char
    - **first_name**: User's first name (2-100 chars)
    - **last_name**: User's last name (2-100 chars)
    - **phone**: Optional phone number
    """
    try:
        auth_service = AuthService(db)

        # Get client info
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("User-Agent")

        # Register user
        user, access_token, refresh_token = auth_service.register_user(
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return RegisterResponse(
            user=UserResponse.model_validate(user),
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

    except DuplicateEmailException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

    except PasswordValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid credentials"},
        403: {"model": ErrorResponse, "description": "Account locked"},
    },
)
async def login(
    login_data: LoginRequest, request: Request, db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens with user details.

    - **email**: User's email address
    - **password**: User's password
    - **remember_me**: Keep user logged in for extended period (default: false)
    - **device_info**: Optional device information for tracking

    When remember_me is true:
    - Access token expires in 30 days (instead of 3 days)
    - Refresh token expires in 90 days (instead of 7 days)
    - Tokens are set as HTTP-only cookies for security

    Returns user details excluding sensitive fields: password, mfa_secret,
    mfa_backup_codes, deleted_at, created_at, updated_at
    """
    try:
        auth_service = AuthService(db)

        # Get client info
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("User-Agent")

        # Login user with remember_me flag
        user, access_token, refresh_token = auth_service.login_user(
            email=login_data.email,
            password=login_data.password,
            remember_me=login_data.remember_me,
            device_info=login_data.device_info.model_dump()
            if login_data.device_info
            else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Get user's organization_id (similar to /me endpoint logic)
        user_org_role = (
            db.query(UserOrganizationRole)
            .filter(
                UserOrganizationRole.user_id == user.id,
                UserOrganizationRole.is_active == True,  # noqa: E712
            )
            .order_by(UserOrganizationRole.is_primary.desc())  # Primary first
            .first()
        )

        organization_id = None
        if user_org_role:
            organization_id = str(user_org_role.organization_id)

        # Create user response with organization_id
        user_dict = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "display_name": user.display_name,
            "phone": user.phone,
            "avatar_url": user.avatar_url,
            "user_type": user.user_type.value if user.user_type else None,
            "status": user.status.value if user.status else None,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "email_verified_at": user.email_verified_at,
            "last_login_at": user.last_login_at,
            "last_login_ip": user.last_login_ip,
            "preferences": user.preferences,
            "timezone": user.timezone,
            "language": user.language,
            "extra_data": user.extra_data,
            "organization_id": organization_id,
        }

        # Calculate expires_in based on remember_me
        if login_data.remember_me:
            expires_in = (
                settings.remember_me_access_token_expire_days * 24 * 60 * 60
            )  # Convert days to seconds
            max_age = (
                settings.remember_me_refresh_token_expire_days * 24 * 60 * 60
            )  # Cookie max age in seconds
        else:
            expires_in = (
                settings.access_token_expire_minutes * 60
            )  # Convert minutes to seconds
            max_age = None  # Session cookie (expires when browser closes)

        # Create response
        response = JSONResponse(
            content={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": expires_in,
                "user": LoginUserResponse.model_validate(user_dict).model_dump(
                    mode="json"
                ),
            }
        )

        # Set cookies for tokens
        # Access token cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=max_age,
            expires=max_age,
            path="/",
            domain=settings.cookie_domain,
            secure=settings.cookie_secure,
            httponly=settings.cookie_httponly,
            samesite=settings.cookie_samesite,
        )

        # Refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=max_age,
            expires=max_age,
            path="/",
            domain=settings.cookie_domain,
            secure=settings.cookie_secure,
            httponly=settings.cookie_httponly,
            samesite=settings.cookie_samesite,
        )

        return response

    except (AuthenticationError, AccountLockedException) as e:
        raise handle_login_errors(login_data.email, e)


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired token"}
    },
)
async def refresh_token(token_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token
    """
    try:
        auth_service = AuthService(db)

        # Generate new access token
        access_token = auth_service.refresh_access_token(token_data.refresh_token)

        return RefreshTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

    except (InvalidTokenException, TokenExpiredException, UserNotFoundException) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e


@router.post(
    "/logout",
    response_model=LogoutResponse,
    responses={404: {"model": ErrorResponse, "description": "Token not found"}},
)
async def logout(logout_data: LogoutRequest, db: Session = Depends(get_db)):
    """
    Logout user by revoking refresh token and clearing cookies.

    No authentication required - the refresh token itself is sufficient.

    - **refresh_token**: Refresh token to revoke
    """
    try:
        auth_service = AuthService(db)

        # Logout user
        auth_service.logout_user(logout_data.refresh_token)

        # Create response
        response = JSONResponse(content={"message": "Successfully logged out"})

        # Clear cookies
        response.delete_cookie(
            key="access_token",
            path="/",
            domain=settings.cookie_domain,
            secure=settings.cookie_secure,
            httponly=settings.cookie_httponly,
            samesite=settings.cookie_samesite,
        )

        response.delete_cookie(
            key="refresh_token",
            path="/",
            domain=settings.cookie_domain,
            secure=settings.cookie_secure,
            httponly=settings.cookie_httponly,
            samesite=settings.cookie_samesite,
        )

        return response

    except InvalidTokenException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "model": ForgotPasswordResponse,
            "description": "Password reset email sent",
        }
    },
)
async def forgot_password(
    request_data: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Request password reset token.

    Sends a password reset email to the user if the email exists.
    For security, always returns success even if email doesn't exist.

    - **email**: User's email address
    """
    import logging

    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Forgot Password Endpoint Called")
    logger.info("=" * 60)
    logger.info(f"Email: {request_data.email}")

    auth_service = AuthService(db)
    email_service = EmailService()

    # Get client info
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")

    logger.info(f"Client IP: {ip_address}")
    logger.info(f"User Agent: {user_agent}")

    # Generate reset token (or skip silently if cooldown is active / unknown email)
    logger.info("Generating reset token...")
    reset_token, retry_after = auth_service.forgot_password(
        email=request_data.email, ip_address=ip_address, user_agent=user_agent
    )

    if reset_token is not None:
        logger.info(f"Reset token generated (length: {len(reset_token)})")
        logger.info("Adding email task to background...")
        background_tasks.add_task(
            email_service.send_password_reset_email,
            recipient=request_data.email,
            token=reset_token,
        )
        logger.info("Email task added to background queue")
    else:
        # Either user doesn't exist OR a previous token is still within the
        # cooldown window. Either way, do not send a new email — and crucially
        # do not differentiate the two cases in the response.
        logger.info(
            f"Skipping email send (cooldown active or unknown email); "
            f"retry_after={retry_after}s"
        )
    logger.info("=" * 60)

    # Generic response — same message and retry hint regardless of whether the
    # email is registered or whether we just skipped due to cooldown.
    return ForgotPasswordResponse(
        message="If the email exists, a password reset link has been sent",
        retry_after_seconds=retry_after,
    )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid password"},
        401: {"model": ErrorResponse, "description": "Invalid or expired token"},
    },
)
async def reset_password(
    request_data: ResetPasswordRequest, db: Session = Depends(get_db)
):
    """
    Reset password using reset token.

    - **token**: Password reset token from email
    - **new_password**: New password (min 8 chars, must contain uppercase, lowercase, number, special char)
    """
    try:
        auth_service = AuthService(db)

        # Reset password
        auth_service.reset_password(
            token=request_data.token, new_password=request_data.new_password
        )

        return ResetPasswordResponse(
            message="Password has been reset successfully. Please login with your new password."
        )

    except PasswordValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    except (InvalidTokenException, UserNotFoundException) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e


@router.get(
    "/verify-reset-token",
    response_model=VerifyResetTokenResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_reset_token(token: str, db: Session = Depends(get_db)):
    """
    Verify whether a password-reset token is still valid (unused & unexpired).

    Used by the front-end to show an "expired link" page immediately if the
    user revisits a reset-password URL after consuming it, instead of waiting
    until form submission.
    """
    auth_service = AuthService(db)
    return VerifyResetTokenResponse(
        valid=auth_service.is_password_reset_token_valid(token)
    )


@router.post(
    "/token",
    response_model=ServiceTokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid client credentials"},
        400: {"model": ErrorResponse, "description": "Unsupported grant type"},
    },
    summary="Obtain a service token (client-credentials)",
    description="Machine-to-machine OAuth2 endpoint. Used by services like ai-service to get a JWT with embedded permissions.",
)
async def client_credentials_token(
    request_data: ClientCredentialsRequest, db: Session = Depends(get_db)
):
    """Exchange a client_id + client_secret for a short-lived service JWT.

    The returned token has ``type: "service"`` in its payload so that
    core-service can distinguish it from a human user token and read
    permissions directly from the JWT instead of calling ``/me``.
    """
    if request_data.grant_type != "client_credentials":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported grant_type. Use 'client_credentials'.",
        )

    credential = (
        db.query(ServiceCredential)
        .filter(
            ServiceCredential.client_id == request_data.client_id,
            ServiceCredential.is_active == True,  # noqa: E712
        )
        .first()
    )

    if not credential or not verify_client_secret(
        request_data.client_secret, credential.client_secret_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last_used_at
    credential.last_used_at = datetime.now(UTC)
    db.commit()

    token_data = {
        "sub": f"service:{credential.client_id}",
        "service_name": credential.service_name,
        "permissions": credential.permissions or [],
        "scopes": credential.scopes,
    }
    access_token = create_service_token(token_data)

    return ServiceTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.service_token_expire_minutes * 60,
    )


@router.get(
    "/me",
    response_model=dict,
    summary="Get current user info",
    description="Get current authenticated user information including organization_id",
)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current authenticated user information.

    Returns user details including organization_id and permissions from their primary organization role.
    Used by core-service and other clients for RBAC (role-based access control).

    **Returns:**
    - User information
    - organization_id: Primary organization UUID
    - permissions: List of permission codes (e.g. item.read, warehouse.create)
    """
    # Get user's primary organization, or fallback to any active organization
    user_org_role = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == current_user.id,
            UserOrganizationRole.is_active == True,  # noqa: E712
        )
        .order_by(UserOrganizationRole.is_primary.desc())  # Primary first
        .first()
    )

    organization_id = None
    if user_org_role:
        organization_id = str(user_org_role.organization_id)

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "display_name": current_user.display_name,
        "user_type": current_user.user_type.value if current_user.user_type else None,
        "status": current_user.status.value if current_user.status else None,
        "organization_id": organization_id,
        "permissions": current_user.permissions,
    }


# ──────────────────────────────────────────────────────────────────────
# QR Code Login (Warehouse Workers)
# ──────────────────────────────────────────────────────────────────────


@router.post(
    "/login/barcode",
    response_model=QRCodeLoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid barcode"},
        403: {"model": ErrorResponse, "description": "Not a warehouse worker"},
    },
    summary="Barcode login for warehouse workers (legacy path)",
    description="Backward-compatible alias for /login/qr-code. Accepts 'barcode' field.",
)
@router.post(
    "/login/qr-code",
    response_model=QRCodeLoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid QR code"},
        403: {"model": ErrorResponse, "description": "Not a warehouse worker"},
    },
    summary="QR code login for warehouse workers",
    description="Warehouse workers authenticate by scanning a QR code. Returns JWT tokens.",
)
async def qr_code_login(
    body: QRCodeLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Authenticate a warehouse worker using their unique QR code.

    The worker scans a QR code with their mobile device. The app extracts
    the QR code string and sends it here to obtain JWT access/refresh tokens.

    - **qr_code** (or **barcode**): The worker's unique QR/barcode string (from scan)
    """
    auth_service = AuthService(db)

    # Support both "qr_code" and "barcode" field names (backward compat)
    code = body.qr_code or body.barcode
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either qr_code or barcode is required",
        )

    ip_address = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")

    try:
        user, access_token, refresh_token = auth_service.login_by_qr_code(
            qr_code=code,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e

    # Get user's organization_id
    user_org_role = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == user.id,
            UserOrganizationRole.is_active == True,  # noqa: E712
        )
        .order_by(UserOrganizationRole.is_primary.desc())
        .first()
    )
    organization_id = str(user_org_role.organization_id) if user_org_role else None

    user_dict = {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "display_name": user.display_name,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "user_type": user.user_type.value if user.user_type else None,
        "status": user.status.value if user.status else None,
        "is_active": user.is_active,
        "email_verified": user.email_verified,
        "email_verified_at": user.email_verified_at,
        "last_login_at": user.last_login_at,
        "last_login_ip": user.last_login_ip,
        "preferences": user.preferences,
        "timezone": user.timezone,
        "language": user.language,
        "extra_data": user.extra_data,
        "organization_id": organization_id,
    }

    worker_ttl_hours = getattr(settings, "worker_token_expire_hours", 20)
    expires_in = worker_ttl_hours * 60 * 60

    return QRCodeLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=LoginUserResponse.model_validate(user_dict),
    )


@router.get(
    "/workers/{user_id}/qr-image",
    responses={
        404: {"model": ErrorResponse, "description": "Worker not found"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
    },
    summary="Generate QR code image for a warehouse worker",
    description="Admin downloads a QR code PNG image for a worker. The worker scans it to log in.",
)
async def get_worker_qr_image(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("warehouse.manage")),
):
    """
    Generate a printable QR code image for a warehouse worker.

    The QR code encodes the worker's unique qr_code string. When scanned
    by the mobile app, it is sent to POST /login/qr-code to authenticate.

    Requires `warehouse.manage` permission.
    """
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(db)
    worker = user_repo.get_user_by_id(user_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    if worker.user_type != UserType.WAREHOUSE_WORKER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a warehouse worker",
        )

    qr_code_value = worker.qr_code
    if not qr_code_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Worker has no QR code assigned. Create the worker first.",
        )

    # Generate QR code image encoding just the qr_code string
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_code_value)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={
            "Content-Disposition": f"inline; filename=worker-qr-{qr_code_value}.png"
        },
    )
