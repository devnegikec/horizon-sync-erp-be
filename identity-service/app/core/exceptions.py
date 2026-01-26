"""Custom exception classes for the application"""


class AuthenticationError(Exception):
    """Raised when authentication fails"""

    pass


class AccountLockedException(Exception):
    """Raised when account is locked due to failed login attempts"""

    pass


class TokenExpiredException(Exception):
    """Raised when a token has expired"""

    pass


class InvalidTokenException(Exception):
    """Raised when a token is invalid or malformed"""

    pass


class UserNotFoundException(Exception):
    """Raised when a user is not found"""

    pass


class DuplicateEmailException(Exception):
    """Raised when attempting to create a user with an existing email"""

    pass


class PasswordValidationException(Exception):
    """Raised when password doesn't meet requirements"""

    pass


class InsufficientPermissionsException(Exception):
    """Raised when user lacks required permissions"""

    pass
