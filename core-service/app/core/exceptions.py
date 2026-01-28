"""Custom exception classes for the application"""


class CoreServiceException(Exception):
    """Base exception for core service"""

    pass


# ===========================================
# INVENTORY EXCEPTIONS
# ===========================================


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


class DuplicateWarehouseCodeException(CoreServiceException):
    """Raised when warehouse code already exists"""

    pass


class ItemPriceNotFoundException(CoreServiceException):
    """Raised when an item price is not found"""

    pass


class DuplicateItemPriceException(CoreServiceException):
    """Raised when item price with same conditions already exists"""

    pass


# ===========================================
# CUSTOMER/SUPPLIER EXCEPTIONS
# ===========================================


class CustomerNotFoundException(CoreServiceException):
    """Raised when a customer is not found"""

    pass


class SupplierNotFoundException(CoreServiceException):
    """Raised when a supplier is not found"""

    pass


class DuplicateCustomerCodeException(CoreServiceException):
    """Raised when customer code already exists"""

    pass


class DuplicateSupplierCodeException(CoreServiceException):
    """Raised when supplier code already exists"""

    pass


# ===========================================
# ACCOUNTING EXCEPTIONS
# ===========================================


class ChartOfAccountNotFoundException(CoreServiceException):
    """Raised when a chart of account is not found"""

    pass


class DuplicateAccountCodeException(CoreServiceException):
    """Raised when account code already exists"""

    pass


# ===========================================
# GENERAL EXCEPTIONS
# ===========================================


class AuthenticationError(CoreServiceException):
    """Raised when authentication fails"""

    pass


class AuthorizationError(CoreServiceException):
    """Raised when user lacks permission"""

    pass


class ValidationError(CoreServiceException):
    """Raised when validation fails"""

    pass


class ValidationException(CoreServiceException):
    """Raised when validation fails"""

    pass


class CircularReferenceException(CoreServiceException):
    """Raised when a circular reference is detected in hierarchical data"""

    pass


class CannotDeleteException(CoreServiceException):
    """Raised when an entity cannot be deleted due to dependencies"""

    pass
