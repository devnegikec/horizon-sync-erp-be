"""Authentication API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    LogoutRequest,
    LogoutResponse,
    RegisterResponse
)
from app.schemas.user import UserCreate, UserResponse
from app.schemas.error import ErrorResponse
from app.services.auth_service import AuthService
from app.dependencies import get_current_user, get_client_ip
from app.core.exceptions import (
    AuthenticationError,
    AccountLockedException,
    DuplicateEmailException,
    PasswordValidationException,
    InvalidTokenException,
    TokenExpiredException,
    UserNotFoundException
)
from app.config import settings

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        409: {"model": ErrorResponse, "description": "Email already exists"}
    }
)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
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
            user_agent=user_agent
        )
        
        return RegisterResponse(
            user=UserResponse.model_validate(user),
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )
    
    except DuplicateEmailException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    
    except PasswordValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid credentials"},
        403: {"model": ErrorResponse, "description": "Account locked"}
    }
)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.
    
    - **email**: User's email address
    - **password**: User's password
    - **device_info**: Optional device information for tracking
    """
    try:
        auth_service = AuthService(db)
        
        # Get client info
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("User-Agent")
        
        # Login user
        user, access_token, refresh_token = auth_service.login_user(
            email=login_data.email,
            password=login_data.password,
            device_info=login_data.device_info.model_dump() if login_data.device_info else None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )
    
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    
    except AccountLockedException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired token"}
    }
)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
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
            expires_in=settings.access_token_expire_minutes * 60
        )
    
    except (InvalidTokenException, TokenExpiredException, UserNotFoundException) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Token not found"}
    }
)
async def logout(
    logout_data: LogoutRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout user by revoking refresh token.
    
    Requires authentication via access token in Authorization header.
    
    - **refresh_token**: Refresh token to revoke
    """
    try:
        auth_service = AuthService(db)
        
        # Logout user
        auth_service.logout_user(logout_data.refresh_token)
        
        return LogoutResponse(message="Successfully logged out")
    
    except InvalidTokenException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
