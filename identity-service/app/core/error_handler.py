"""Error handling utilities for consistent error responses across the application"""

from typing import Any

from fastapi import HTTPException, status

from app.core.exceptions import (
    AccountLockedException,
    AuthenticationError,
    DuplicateEmailException,
    InvalidTokenException,
    PasswordValidationException,
    TokenExpiredException,
    UserNotFoundException,
)


class ErrorMessages:
    """Centralized error messages for consistent responses"""

    # Authentication errors
    INVALID_CREDENTIALS = "Invalid email or password"
    ACCOUNT_LOCKED = "Account has been locked due to multiple failed login attempts. Please try again later or contact support."
    ACCOUNT_SUSPENDED = (
        "Your account has been suspended. Please contact support for assistance."
    )
    ACCOUNT_INACTIVE = (
        "Your account is currently inactive. Please contact support for assistance."
    )
    UNAUTHORIZED = "Authentication required"

    # Token errors
    TOKEN_EXPIRED = "Token has expired. Please login again."
    INVALID_TOKEN = "Invalid or malformed token"
    REFRESH_TOKEN_INVALID = "Invalid refresh token. Please login again."

    # User errors
    USER_NOT_FOUND = "User not found"
    EMAIL_ALREADY_EXISTS = "An account with this email already exists"

    # Password errors
    WEAK_PASSWORD = "Password must be at least 8 characters long and contain uppercase, lowercase, number, and special character"
    PASSWORD_MISMATCH = "Passwords do not match"

    # General errors
    VALIDATION_ERROR = "Validation error occurred"
    INTERNAL_ERROR = "An unexpected error occurred. Please try again later."
    RATE_LIMIT_EXCEEDED = "Too many requests. Please try again later."


def create_error_response(
    status_code: int,
    message: str,
    error_code: str = None,
    details: dict[str, Any] = None,
) -> dict[str, Any]:
    """
    Create a standardized error response structure

    Args:
        status_code: HTTP status code
        message: Error message
        error_code: Optional error code for client-side handling
        details: Optional additional error details

    Returns:
        Standardized error response dictionary
    """
    error_response = {
        "error": {
            "message": message,
            "status_code": status_code,
        }
    }

    if error_code:
        error_response["error"]["code"] = error_code

    if details:
        error_response["error"]["details"] = details

    return error_response


def handle_auth_error(error: Exception) -> HTTPException:
    """
    Handle authentication-related errors and return appropriate HTTP exceptions

    Args:
        error: The exception that was raised

    Returns:
        HTTPException with appropriate status code and message
    """
    if isinstance(error, AuthenticationError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_error_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=ErrorMessages.INVALID_CREDENTIALS,
                error_code="INVALID_CREDENTIALS",
            )["error"],
        )

    elif isinstance(error, AccountLockedException):
        return HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=create_error_response(
                status_code=status.HTTP_423_LOCKED,
                message=ErrorMessages.ACCOUNT_LOCKED,
                error_code="ACCOUNT_LOCKED",
            )["error"],
        )

    elif isinstance(error, TokenExpiredException):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_error_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=ErrorMessages.TOKEN_EXPIRED,
                error_code="TOKEN_EXPIRED",
            )["error"],
        )

    elif isinstance(error, InvalidTokenException):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_error_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=ErrorMessages.INVALID_TOKEN,
                error_code="INVALID_TOKEN",
            )["error"],
        )

    elif isinstance(error, UserNotFoundException):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=create_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message=ErrorMessages.USER_NOT_FOUND,
                error_code="USER_NOT_FOUND",
            )["error"],
        )

    elif isinstance(error, DuplicateEmailException):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=create_error_response(
                status_code=status.HTTP_409_CONFLICT,
                message=ErrorMessages.EMAIL_ALREADY_EXISTS,
                error_code="EMAIL_ALREADY_EXISTS",
            )["error"],
        )

    elif isinstance(error, PasswordValidationException):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=str(error),
                error_code="WEAK_PASSWORD",
            )["error"],
        )

    else:
        # Generic error handling
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=ErrorMessages.INTERNAL_ERROR,
                error_code="INTERNAL_ERROR",
            )["error"],
        )


def handle_login_errors(email: str, error: Exception) -> HTTPException:
    """
    Handle login-specific errors with appropriate messages

    Args:
        email: User's email (for logging purposes)
        error: The exception that was raised

    Returns:
        HTTPException with appropriate status code and message
    """
    if isinstance(error, AuthenticationError):
        # `login_user` raises AuthenticationError for several distinct cases.
        # Detect "account inactive / suspended" so users see a useful message
        # (and aren't misled into thinking their password is wrong after a
        # successful reset).
        original = str(error).lower()
        if "inactive" in original or "suspended" in original:
            return HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=create_error_response(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message=ErrorMessages.ACCOUNT_SUSPENDED,
                    error_code="ACCOUNT_SUSPENDED",
                )["error"],
            )
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_error_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=ErrorMessages.INVALID_CREDENTIALS,
                error_code="INVALID_CREDENTIALS",
            )["error"],
        )

    elif isinstance(error, AccountLockedException):
        return HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=create_error_response(
                status_code=status.HTTP_423_LOCKED,
                message=ErrorMessages.ACCOUNT_LOCKED,
                error_code="ACCOUNT_LOCKED",
            )["error"],
        )

    else:
        return handle_auth_error(error)
