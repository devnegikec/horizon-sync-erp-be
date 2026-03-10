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


class UOMNotFoundException(CoreServiceException):
    """Raised when a UOM is not found"""

    pass


class DuplicateUOMNameException(CoreServiceException):
    """Raised when UOM name already exists in the organization"""

    pass


class DuplicateUOMAbbreviationException(CoreServiceException):
    """Raised when UOM abbreviation already exists in the organization"""

    pass


class UOMConversionNotFoundException(CoreServiceException):
    """Raised when a UOM conversion is not found"""

    pass


class DuplicateUOMConversionException(CoreServiceException):
    """Raised when UOM conversion (item_id, from_uom, to_uom) already exists in the organization"""

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


class DuplicateItemPriceException(CoreServiceException):
    """Raised when item price with same conditions already exists"""

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


class CurrencyNotFoundException(CoreServiceException):
    """Raised when a currency is not found or not supported"""

    pass


class DuplicateCurrencyCodeException(CoreServiceException):
    """Raised when currency code already exists in the organization"""

    pass


class ExchangeRateNotFoundException(CoreServiceException):
    """Raised when an exchange rate is not found for a currency pair and date"""

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
    """Raised when validation fails (HTTP 400)

    Attributes:
        message: Human-readable error message
        details: List of validation errors with field and reason
    """

    def __init__(self, message: str, details: list[dict[str, str]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or []
        self.status_code = 400
        self.error_code = "VALIDATION_ERROR"


class ValidationException(CoreServiceException):
    """Raised when validation fails"""

    pass


class CircularReferenceException(CoreServiceException):
    """Raised when a circular reference is detected in hierarchical data"""

    pass


class CannotDeleteException(CoreServiceException):
    """Raised when an entity cannot be deleted due to dependencies"""

    pass


class ResourceNotFoundException(CoreServiceException):
    """Raised when a resource (e.g. quality template, inspection) is not found"""

    pass


# ===========================================
# SOURCING FLOW ERROR HANDLERS
# ===========================================


class NotFoundError(CoreServiceException):
    """Raised when a referenced entity is not found (HTTP 404)

    Attributes:
        message: Human-readable error message
        entity_type: Type of entity that was not found
        entity_id: ID of the entity that was not found
    """

    def __init__(self, message: str, entity_type: str, entity_id: str):
        super().__init__(message)
        self.message = message
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.status_code = 404
        self.error_code = "NOT_FOUND"


class StateError(CoreServiceException):
    """Raised when an operation conflicts with current state (HTTP 409)

    Attributes:
        message: Human-readable error message
        current_state: Current state of the entity
        required_state: List of valid states for the operation
    """

    def __init__(self, message: str, current_state: str, required_state: list[str]):
        super().__init__(message)
        self.message = message
        self.current_state = current_state
        self.required_state = required_state
        self.status_code = 409
        self.error_code = "STATE_CONFLICT"


class IntegrationError(CoreServiceException):
    """Raised when external API calls fail (HTTP 502/503)

    Attributes:
        message: Human-readable error message
        service: Name of the external service that failed
        details: Optional additional details about the failure
        status_code: HTTP status code (502 or 503)
    """

    def __init__(
        self, message: str, service: str, details: str = None, status_code: int = 502
    ):
        super().__init__(message)
        self.message = message
        self.service = service
        self.details = details
        self.status_code = status_code if status_code in [502, 503] else 502
        self.error_code = "INTEGRATION_ERROR"


# ===========================================
# BANK ACCOUNT EXCEPTIONS
# ===========================================


class BankAccountNotFoundException(CoreServiceException):
    """Raised when a bank account is not found"""

    pass


class DuplicateIbanException(CoreServiceException):
    """Raised when IBAN already exists for the organization"""

    pass


class InvalidAccountStateException(CoreServiceException):
    """Raised when trying to perform an invalid state transition"""

    pass


class UnauthorizedException(CoreServiceException):
    """Raised when user doesn't have permission for the operation"""

    pass


class ReconciledTransactionDeletionException(CoreServiceException):
    """Raised when attempting to delete a bank account with reconciled transactions"""
    pass
