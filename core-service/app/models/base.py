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

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
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
    SUBSCRIPTION = "subscription"  # Task 1B-1: Subscription invoice support
    SETUP_FEE = "setup_fee"  # Task 1F-1: Setup fee invoices for new customers
    OVERAGE = "overage"  # Task 1F-1: Overage charges for usage limits
    ADDON = "addon"  # Task 1F-1: Add-on service invoices
    CREDIT_ADJUSTMENT = "credit_adjustment"  # Task 1F-1: Credit notes and adjustments


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


class BillingCycle(str, enum.Enum):
    """Billing cycle enumeration for subscription invoices (Task 1B-1)"""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class JournalStatus(str, enum.Enum):
    """Journal entry status enumeration"""

    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"


class DefaultAccountTransactionType(str, enum.Enum):
    """Transaction type enumeration for default account mappings"""

    ACCOUNTS_RECEIVABLE = "accounts_receivable"
    SALES_REVENUE = "sales_revenue"
    ACCOUNTS_PAYABLE = "accounts_payable"
    PURCHASE_EXPENSE = "purchase_expense"
    INVENTORY_ASSET = "inventory_asset"
    COST_OF_GOODS_SOLD = "cost_of_goods_sold"
    CASH = "cash"
    BANK = "bank"
    CHECKS_RECEIVED = "checks_received"
    DEMAND_DRAFT = "demand_draft"
    TAX_PAYABLE = "tax_payable"
    TAX_RECEIVABLE = "tax_receivable"
    DISCOUNT_GIVEN = "discount_given"
    DISCOUNT_RECEIVED = "discount_received"
    FREIGHT_EXPENSE = "freight_expense"
    SHIPPING_CHARGES = "shipping_charges"
    INVENTORY_PURCHASE = "inventory_purchase"
    INVENTORY_SALE = "inventory_sale"
    SALES_INVOICE = "sales_invoice"
    PURCHASE_INVOICE = "purchase_invoice"


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


class AsnOrderStatus(str, enum.Enum):
    """Advance Stock Notice (ASN) order status enumeration"""

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
    DEMAND_DRAFT = "Demand_Draft"


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


# ===========================================
# BANKING ENUMS
# ===========================================


class TransactionStatus(str, enum.Enum):
    """Bank transaction status enumeration"""

    PENDING = "pending"
    CLEARED = "cleared"
    RECONCILED = "reconciled"
    VOID = "void"


class TransactionTypeEnum(str, enum.Enum):
    """Bank transaction type enumeration"""

    DEBIT = "debit"
    CREDIT = "credit"


class ReconciliationType(str, enum.Enum):
    """Bank reconciliation type enumeration"""

    MANUAL = "manual"
    AUTO_EXACT = "auto_exact"
    AUTO_FUZZY = "auto_fuzzy"
    MANY_TO_ONE = "many_to_one"


class ReconciliationStatus(str, enum.Enum):
    """Bank reconciliation status enumeration"""

    SUGGESTED = "suggested"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class BankAccountHistoryAction(str, enum.Enum):
    """Bank account history action enumeration"""

    CREATED = "created"
    UPDATED = "updated"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"


# ===========================================
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
    ASN = "asn"


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


class NotificationType(str, enum.Enum):
    """In-app notification type enumeration for WMS/ASN events"""

    ASN_CREATED = "asn_created"
    ASN_CONFIRMED = "asn_confirmed"
    ASN_CANCELLED = "asn_cancelled"
    FULFILLMENT_INITIATED = "fulfillment_initiated"
    FULFILLMENT_COMPLETED = "fulfillment_completed"
    FULFILLMENT_PARTIALLY_COMPLETED = "fulfillment_partially_completed"
    RECEIVING_SLIP_CREATED = "receiving_slip_created"
    PUT_AWAY_LIST_CREATED = "put_away_list_created"
    PICK_LIST_CREATED = "pick_list_created"
    PICK_EXCEPTION = "pick_exception"
    ERP_SYNC_FAILED = "erp_sync_failed"
    TRANSFER_PICK_CREATED = "transfer_pick_created"


class WarehouseUserRole(str, enum.Enum):
    """Role of a user assigned to a warehouse"""

    SUPERVISOR = "supervisor"
    MANAGER = "manager"
    OPERATOR = "operator"
    COORDINATOR = "coordinator"
