"""Base model and enum definitions for inventory management"""

import enum

# ===========================================
# INVENTORY ENUMS
# ===========================================


class ItemType(str, enum.Enum):
    """Item type enumeration"""

    STOCK = "stock"
    NON_STOCK = "non_stock"
    SERVICE = "service"
    FIXED_ASSET = "fixed_asset"


class ItemStatus(str, enum.Enum):
    """Item status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"


class ValuationMethod(str, enum.Enum):
    """Inventory valuation method enumeration"""

    FIFO = "fifo"
    LIFO = "lifo"
    MOVING_AVERAGE = "moving_average"
    STANDARD = "standard"


class DocumentStatus(str, enum.Enum):
    """Document status enumeration"""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"


class WarehouseType(str, enum.Enum):
    """Warehouse type enumeration"""

    WAREHOUSE = "warehouse"
    STORE = "store"
    VIRTUAL = "virtual"
    TRANSIT = "transit"


class BatchStatus(str, enum.Enum):
    """Batch status enumeration"""

    ACTIVE = "active"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class StockEntryType(str, enum.Enum):
    """Stock entry type enumeration"""

    MATERIAL_RECEIPT = "material_receipt"
    MATERIAL_ISSUE = "material_issue"
    MATERIAL_TRANSFER = "material_transfer"
    MANUFACTURE = "manufacture"
    REPACK = "repack"
    SEND_TO_SUBCONTRACTOR = "send_to_subcontractor"


class StockEntryStatus(str, enum.Enum):
    """Stock entry status enumeration"""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"


class MovementType(str, enum.Enum):
    """Movement type enumeration"""

    IN = "in"
    OUT = "out"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"


class InspectionType(str, enum.Enum):
    """Quality inspection type enumeration"""

    INCOMING = "incoming"
    OUTGOING = "outgoing"
    IN_PROCESS = "in_process"


class InspectionStatus(str, enum.Enum):
    """Quality inspection status enumeration"""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ReadingType(str, enum.Enum):
    """Quality inspection reading type enumeration"""

    NUMERIC = "numeric"
    TEXT = "text"
    PASS_FAIL = "pass_fail"


# ===========================================
# CUSTOMER/SUPPLIER ENUMS
# ===========================================


class CustomerStatus(str, enum.Enum):
    """Customer status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class SupplierStatus(str, enum.Enum):
    """Supplier status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


# ===========================================
# ACCOUNTING/BILLING ENUMS
# ===========================================


class AccountType(str, enum.Enum):
    """Account type enumeration for Chart of Accounts"""

    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


class InvoiceType(str, enum.Enum):
    """Invoice type enumeration"""

    SALES = "sales"
    PURCHASE = "purchase"


class InvoiceStatus(str, enum.Enum):
    """Invoice status enumeration"""

    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentType(str, enum.Enum):
    """Payment type enumeration"""

    RECEIVE = "receive"
    PAY = "pay"


class PaymentStatus(str, enum.Enum):
    """Payment status enumeration"""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    """Payment method enumeration"""

    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CHEQUE = "cheque"
    UPI = "upi"
    OTHER = "other"


class JournalStatus(str, enum.Enum):
    """Journal entry status enumeration"""

    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"


# ===========================================
# ORDER PROCESSING ENUMS
# ===========================================


class PickListStatus(str, enum.Enum):
    """Pick list status enumeration"""

    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
