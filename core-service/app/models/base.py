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
    REVENUE = "revenue"
    EXPENSE = "expense"


class AccountStatus(str, enum.Enum):
    """Account status enumeration (values match PostgreSQL accountstatus enum)."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


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


class QuotationStatus(str, enum.Enum):
    """Quotation status enumeration"""

    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class SalesOrderStatus(str, enum.Enum):
    """Sales order status enumeration"""

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PARTIALLY_DELIVERED = "partially_delivered"
    DELIVERED = "delivered"
    CLOSED = "closed"
    CANCELLED = "cancelled"


# ===========================================
# SOURCING/PROCUREMENT ENUMS
# ===========================================


class MaterialRequestType(str, enum.Enum):
    """Material request type enumeration"""

    PURCHASE = "purchase"  # Buy from vendor
    TRANSFER = "transfer"  # Move from Warehouse A to B
    ISSUE = "issue"  # Give to a department


class MaterialRequestPriority(str, enum.Enum):
    """Material request priority enumeration"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MaterialRequestStatus(str, enum.Enum):
    """Material request status enumeration"""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    PARTIALLY_QUOTED = "partially_quoted"
    FULLY_QUOTED = "fully_quoted"
    CANCELLED = "cancelled"


class RFQStatus(str, enum.Enum):
    """RFQ status enumeration"""

    DRAFT = "draft"
    SENT = "sent"
    PARTIALLY_RESPONDED = "partially_responded"
    FULLY_RESPONDED = "fully_responded"
    CLOSED = "closed"


class PurchaseOrderStatus(str, enum.Enum):
    """Purchase order status enumeration"""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    PARTIALLY_RECEIVED = "partially_received"
    FULLY_RECEIVED = "fully_received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TransactionType(str, enum.Enum):
    """Transaction type enumeration for Transaction Engine"""

    PURCHASE = "purchase"
    SALES = "sales"


# ===========================================
# PAYMENT FLOW ENUMS
# ===========================================


class PaymentEntryType(str, enum.Enum):
    """Payment entry type enumeration"""

    CUSTOMER_PAYMENT = "Customer_Payment"
    SUPPLIER_PAYMENT = "Supplier_Payment"


class PaymentMode(str, enum.Enum):
    """Payment mode enumeration"""

    CASH = "Cash"
    CHECK = "Check"
    BANK_TRANSFER = "Bank_Transfer"


class PaymentEntryStatus(str, enum.Enum):
    """Payment entry status enumeration"""

    DRAFT = "Draft"
    CONFIRMED = "Confirmed"
    CANCELLED = "Cancelled"


class PaymentSource(str, enum.Enum):
    """Payment source enumeration"""

    MANUAL = "Manual"
    STRIPE = "Stripe"
    RAZORPAY = "Razorpay"


class PaymentAuditAction(str, enum.Enum):
    """Payment audit action enumeration"""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    CONFIRM = "CONFIRM"
    CANCEL = "CANCEL"
    ALLOCATE = "ALLOCATE"
    DEALLOCATE = "DEALLOCATE"


# COMMUNICATION ENUMS
# ===========================================


class CommunicationDocType(str, enum.Enum):
    """Communication document type enumeration"""

    QUOTATION = "quotation"
    SALES_ORDER = "sales_order"
    PURCHASE_ORDER = "purchase_order"
    INVOICE = "invoice"
    DELIVERY_NOTE = "delivery_note"
    PURCHASE_RECEIPT = "purchase_receipt"
    PAYMENT = "payment"
    RFQ = "rfq"
    MATERIAL_REQUEST = "material_request"


class CommunicationChannel(str, enum.Enum):
    """Communication channel enumeration"""

    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    WEBHOOK = "webhook"


class CommunicationStatus(str, enum.Enum):
    """Communication status enumeration"""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


class RecipientType(str, enum.Enum):
    """Recipient type enumeration"""

    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    EMPLOYEE = "employee"
    OTHER = "other"
