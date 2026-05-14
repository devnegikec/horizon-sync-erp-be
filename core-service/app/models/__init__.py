"""Database models package"""

from app.models.account_audit_log import AccountAuditLog, AuditAction
from app.models.account_balance import AccountBalance

# Admin Portal module
from app.models.admin import (
    AdminAuditLog,
    AdminNotification,
    UserActivityLog,
)

# Analytics module
# Analytics module
from app.models.analytics import MetaCampaign

# Audit Trail module
from app.models.audit_log import AuditAction as AuditLogAction
from app.models.audit_log import AuditLog
from app.models.bank_account import BankAccount, BankAccountHistory
from app.models.bank_reconciliation import BankReconciliation
from app.models.bank_transaction import BankTransaction
from app.models.base import (
    AccountStatus,
    AccountType,
    BankAccountHistoryAction,
    BatchStatus,
    CustomerStatus,
    DocumentStatus,
    InspectionStatus,
    InspectionType,
    InvoiceStatus,
    InvoiceType,
    ItemStatus,
    ItemType,
    JournalStatus,
    MaterialRequestStatus,
    MovementType,
    PaymentAuditAction,
    PaymentEntryStatus,
    PaymentEntryType,
    PaymentMethod,
    PaymentMode,
    PaymentSource,
    PaymentStatus,
    PaymentType,
    PickListStatus,
    PurchaseOrderStatus,
    QuotationStatus,
    ReadingType,
    ReconciliationStatus,
    ReconciliationType,
    RFQStatus,
    SalesOrderStatus,
    StockEntryStatus,
    StockEntryType,
    SupplierStatus,
    TransactionStatus,
    TransactionType,
    TransactionTypeEnum,
    ValuationMethod,
    WarehouseType,
)
from app.models.batch import Batch

# QR Products module
from app.models.brand import Brand

# Brand Trust module
# Brand Trust module
from app.models.brand_trust import (
    BrandIndustry,
    BrandTrustAnswer,
    BrandTrustAssessment,
    BrandTrustQuestion,
)

# Campaigns & Coupons module
from app.models.campaign import Campaign, Play2WinPrize, WebCampaign
from app.models.charge_template import ChargeTemplate
from app.models.chart_of_account import Account
from app.models.coupon import (
    CampaignLead,
    CampaignTag,
    Coupon,
    CouponDuration,
    CouponUnlockLog,
    ExternalCoupon,
    ShopifyConfig,
)
from app.models.currency_master import CurrencyMaster
from app.models.customer import Customer
from app.models.default_account import DefaultAccount

# Destinations module
# Destinations module
from app.models.destination_market import DestinationMarket
from app.models.exchange_rate import ExchangeRate

# Feature Flag module
from app.models.feature_flag import FeatureFlag
from app.models.invoice import Invoice
from app.models.item import Item
from app.models.item_group import ItemGroup
from app.models.journal_entry import JournalEntry, JournalEntryLine

# Messaging module
# Messaging module
from app.models.messaging import (
    BulkMessageJob,
    MessageCredit,
    MessageTemplate,
    RCSCredential,
    RCSReport,
    RCSTemplate,
    ScheduledMessage,
    SMSReport,
    WhatsAppReport,
)
from app.models.payment_audit_log import PaymentAuditLog
from app.models.payment_entry import PaymentEntry
from app.models.payment_reference import PaymentReference
from app.models.product_item import ProductItem

# Public Marketing module
# Public Marketing module
from app.models.public_submission import PublicSubmission
from app.models.qr_activation import QRActivationParameters, QRActivationTrack
from app.models.qr_block import QRBlock
from app.models.qr_credit import QRCreditBalance, QRCreditLedger, QRCreditUsage
from app.models.qr_product import QRProduct
from app.models.qr_scan_event import QRScanEvent
from app.models.quotation import Quotation, QuotationItem

# Reminder Configuration module (Task 1D-1)
from app.models.reminder_config import (
    ReminderConfig,
    ReminderLog,
    ReminderStage,
    ReminderStatus,
    ReminderType,
)
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.serial_no import SerialNo

# URL Management module
# URL Management module
from app.models.short_url import ShortURL
from app.models.stock_entry import StockEntry, StockEntryItem
from app.models.stock_level import StockLevel
from app.models.stock_movement import StockMovement
from app.models.stock_reconciliation import StockReconciliation, StockReconciliationItem
from app.models.system_config import SystemConfig
from app.models.tax_template import TaxRule, TaxTemplate
from app.models.transaction_breakdown import (
    TransactionChargeBreakdown,
    TransactionTaxBreakdown,
)
from app.models.uom import UOM
from app.models.uom_conversion import UOMConversion
from app.models.warehouse import Warehouse

# Warehouse Bin Management module
from app.models.warehouse_location import (
    AllocationType,
    LocationType,
    PutAwayListItemStatus,
    PutAwayListStatus,
    ScanType,
    WarehouseLocation,
    WorkerTaskStatus,
    WorkerTaskType,
)

# Warranty module
from app.models.warranty import Warranty, WarrantyPeriod

# Temporarily commented out to fix autogenerate - these models have FK to non-existent tables
# from app.models.batch import Batch
# from app.models.item_price import ItemPrice
# from app.models.material_request import MaterialRequest, MaterialRequestLine
# from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
# from app.models.rfq import RFQ, RFQLine, RFQSupplier, SupplierQuote
# from app.models.serial_no import SerialNo
# from app.models.status_transition import StatusTransition
# from app.models.stock_entry import StockEntry, StockEntryItem
# from app.models.stock_level import StockLevel
# from app.models.stock_movement import StockMovement
# from app.models.stock_reconciliation import StockReconciliation, StockReconciliationItem

__all__ = [
    # Inventory Enums
    "ItemType",
    "ItemStatus",
    "ValuationMethod",
    "DocumentStatus",
    "WarehouseType",
    "BatchStatus",
    "StockEntryType",
    "StockEntryStatus",
    "MovementType",
    "InspectionType",
    "InspectionStatus",
    "ReadingType",
    # Customer/Supplier Enums
    "CustomerStatus",
    "SupplierStatus",
    # Accounting/Billing Enums
    "AccountType",
    "AccountStatus",
    "InvoiceType",
    "InvoiceStatus",
    "PaymentType",
    "PaymentStatus",
    "PaymentMethod",
    "JournalStatus",
    # Order Processing Enums
    "PickListStatus",
    "QuotationStatus",
    "SalesOrderStatus",
    # Sourcing/Procurement Enums
    "MaterialRequestStatus",
    "RFQStatus",
    "PurchaseOrderStatus",
    "TransactionType",
    # Payment Flow Enums
    "PaymentEntryType",
    "PaymentMode",
    "PaymentEntryStatus",
    "PaymentSource",
    "PaymentAuditAction",
    # Banking Enums
    "TransactionStatus",
    "TransactionTypeEnum",
    "ReconciliationType",
    "ReconciliationStatus",
    "BankAccountHistoryAction",
    # Models
    "Account",
    "AccountBalance",
    "AccountAuditLog",
    "AuditAction",
    "BankAccount",
    "BankAccountHistory",
    "BankTransaction",
    "BankReconciliation",
    "Customer",
    "DefaultAccount",
    "ExchangeRate",
    "Invoice",
    "Item",
    "ItemGroup",
    "JournalEntry",
    "JournalEntryLine",
    "PaymentEntry",
    "PaymentReference",
    "PaymentAuditLog",
    "Quotation",
    "QuotationItem",
    "SalesOrder",
    "SalesOrderItem",
    "SystemConfig",
    "Warehouse",
    "Customer",
    "Batch",
    "SerialNo",
    "StockEntry",
    "StockEntryItem",
    "StockLevel",
    "StockMovement",
    "StockReconciliation",
    "StockReconciliationItem",
    "TaxTemplate",
    "TaxRule",
    "ChargeTemplate",
    "TransactionTaxBreakdown",
    "TransactionChargeBreakdown",
    "UOM",
    "UOMConversion",
    "CurrencyMaster",
    # QR Products module
    "Brand",
    "QRProduct",
    "QRBlock",
    "ProductItem",
    "QRActivationParameters",
    "QRActivationTrack",
    "QRCreditUsage",
    "QRCreditBalance",
    "QRCreditLedger",
    "QRScanEvent",
    # Campaigns & Coupons module
    "Campaign",
    "Play2WinPrize",
    "WebCampaign",
    "CampaignLead",
    "CampaignTag",
    "Coupon",
    "CouponUnlockLog",
    "ExternalCoupon",
    "CouponDuration",
    "ShopifyConfig",
    # Warranty module
    "Warranty",
    "WarrantyPeriod",
    # Analytics module
    "MetaCampaign",
    # URL Management module
    "ShortURL",
    # Destinations module
    "DestinationMarket",
    # Public Marketing module
    "PublicSubmission",
    # Brand Trust module
    "BrandIndustry",
    "BrandTrustQuestion",
    "BrandTrustAssessment",
    "BrandTrustAnswer",
    # Messaging module
    "MessageTemplate",
    "BulkMessageJob",
    "ScheduledMessage",
    "SMSReport",
    "WhatsAppReport",
    "RCSCredential",
    "RCSTemplate",
    "RCSReport",
    "MessageCredit",
    # Reminder Configuration module (Task 1D-1)
    "ReminderConfig",
    "ReminderLog",
    "ReminderType",
    "ReminderStage",
    "ReminderStatus",
    # Admin Portal module
    "UserActivityLog",
    "AdminAuditLog",
    "AdminNotification",
    "FeatureFlag",
    # Audit Trail module
    "AuditLog",
    "AuditLogAction",
    # Warehouse Bin Management module
    "LocationType",
    "PutAwayListStatus",
    "PutAwayListItemStatus",
    "WorkerTaskType",
    "WorkerTaskStatus",
    "ScanType",
    "AllocationType",
    "WarehouseLocation",
    # Temporarily commented out - models with FK to non-existent tables
    # "Batch",
    # "ItemPrice",
    # "MaterialRequest",
    # "MaterialRequestLine",
    # "RFQ",
    # "RFQLine",
    # "RFQSupplier",
    # "SupplierQuote",
    # "PurchaseOrder",
    # "PurchaseOrderLine",
    # "StatusTransition",
    # "SerialNo",
    # "StockEntry",
    # "StockEntryItem",
    # "StockLevel",
    # "StockMovement",
    # "StockReconciliation",
    # "StockReconciliationItem",
]
