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


class RoleNotFoundException(Exception):
    """Raised when a role is not found"""

    pass


class PermissionNotFoundException(Exception):
    """Raised when a permission is not found"""

    pass


class RolePermissionNotFoundException(Exception):
    """Raised when a role-permission mapping is not found"""

    pass


class DuplicateRoleException(Exception):
    """Raised when attempting to create a role with duplicate code"""

    pass


class DuplicatePermissionException(Exception):
    """Raised when attempting to create a permission with duplicate code"""

    pass


class SystemRoleModificationException(Exception):
    """Raised when attempting to modify a system role"""

    pass


class RoleHasUsersException(Exception):
    """Raised when attempting to delete a role with active user assignments"""

    pass


class RolePermissionAlreadyAssignedException(Exception):
    """Raised when permission is already assigned to role"""

    pass


class ResourceNotFoundException(Exception):
    """Raised when a resource is not found"""

    pass


class DuplicateResourceException(Exception):
    """Raised when a resource already exists"""

    pass


class ValidationException(Exception):
    """Raised when validation fails"""

    pass


class InvitationNotFoundException(Exception):
    """Raised when an invitation is not found"""

    pass


class InvitationExpiredException(Exception):
    """Raised when an invitation has expired"""

    pass


class InvitationAlreadyAcceptedException(Exception):
    """Raised when an invitation has already been accepted"""

    pass


class PermissionDeniedException(Exception):
    """Raised when user doesn't have required permission"""

    pass


class UserAlreadyExistsException(Exception):
    """Raised when user already exists in organization"""

    pass


class OrganizationNotFoundException(Exception):
    """Raised when an organization is not found"""

    pass


class DuplicateOrganizationSlugException(Exception):
    """Raised when attempting to create an organization with an existing slug"""

    pass
