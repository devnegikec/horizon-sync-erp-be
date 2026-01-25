"""Custom exception classes for the application"""


class CoreServiceException(Exception):
    """Base exception for core service"""

    pass


class ItemNotFoundException(CoreServiceException):
    """Raised when an item is not found"""

    pass


class ItemGroupNotFoundException(CoreServiceException):
    """Raised when an item group is not found"""

    pass


class WarehouseNotFoundException(CoreServiceException):
    """Raised when a warehouse is not found"""

    pass


class DuplicateItemCodeException(CoreServiceException):
    """Raised when item code already exists"""

    pass


class DuplicateItemGroupCodeException(CoreServiceException):
    """Raised when item group code already exists"""

    pass


class AuthenticationError(CoreServiceException):
    """Raised when authentication fails"""

    pass


class AuthorizationError(CoreServiceException):
    """Raised when user lacks permission"""

    pass


class ValidationError(CoreServiceException):
    """Raised when validation fails"""

    pass
