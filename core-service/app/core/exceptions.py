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


class BatchNotFoundException(CoreServiceException):
    """Raised when a batch is not found"""

    pass


class DuplicateBatchNoException(CoreServiceException):
    """Raised when batch number already exists for the item"""

    pass


class SerialNoNotFoundException(CoreServiceException):
    """Raised when a serial number is not found"""

    pass


class DuplicateSerialNoException(CoreServiceException):
    """Raised when serial number already exists for the item"""

    pass


class StockEntryNotFoundException(CoreServiceException):
    """Raised when a stock entry is not found"""

    pass


class DuplicateStockEntryNoException(CoreServiceException):
    """Raised when stock entry number already exists"""

    pass


class StockEntryItemNotFoundException(CoreServiceException):
    """Raised when a stock entry item is not found"""

    pass


class StockLevelNotFoundException(CoreServiceException):
    """Raised when a stock level is not found"""

    pass


class StockMovementNotFoundException(CoreServiceException):
    """Raised when a stock movement is not found"""

    pass


class StockReconciliationNotFoundException(CoreServiceException):
    """Raised when a stock reconciliation is not found"""

    pass


class DuplicateReconciliationNoException(CoreServiceException):
    """Raised when reconciliation number already exists"""

    pass


class StockReconciliationItemNotFoundException(CoreServiceException):
    """Raised when a stock reconciliation item is not found"""

    pass


class StockSettingsNotFoundException(CoreServiceException):
    """Raised when stock settings are not found for the organization"""

    pass


class PutAwayRuleNotFoundException(CoreServiceException):
    """Raised when a put away rule is not found"""

    pass


class ItemPriceNotFoundException(CoreServiceException):
    """Raised when an item price is not found"""

    pass


class ItemSupplierNotFoundException(CoreServiceException):
    """Raised when an item supplier is not found"""

    pass


class DuplicateItemSupplierException(CoreServiceException):
    """Raised when (item_id, supplier_id) already exists for the organization"""

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


class CircularReferenceException(CoreServiceException):
    """Raised when a circular reference is detected in hierarchical data"""

    pass


class CannotDeleteException(CoreServiceException):
    """Raised when an entity cannot be deleted due to dependencies"""

    pass
