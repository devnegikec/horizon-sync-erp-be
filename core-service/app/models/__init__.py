"""Database models package"""

from app.models.account_audit_log import AccountAuditLog, AuditAction
from app.models.account_balance import AccountBalance
from app.models.bank_account import BankAccount, BankAccountHistory
from app.models.base import (
    AccountStatus,
    AccountType,
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
    RFQStatus,
    SalesOrderStatus,
    StockEntryStatus,
    StockEntryType,
    SupplierStatus,
    TransactionType,
    ValuationMethod,
    WarehouseType,
    PaymentEntryType,
    PaymentMode,
    PaymentEntryStatus,
    PaymentSource,
    PaymentAuditAction,
    TransactionStatus,
    TransactionTypeEnum,
    ReconciliationType,
    ReconciliationStatus,
    BankAccountHistoryAction,
)
from app.models.batch import Batch
from app.models.charge_template import ChargeTemplate
from app.models.chart_of_account import Account
from app.models.account_balance import AccountBalance
from app.models.account_audit_log import AccountAuditLog, AuditAction
from app.models.bank_account import BankAccount, BankAccountHistory
from app.models.bank_transaction import BankTransaction
from app.models.bank_reconciliation import BankReconciliation
from app.models.currency_master import CurrencyMaster
from app.models.customer import Customer
from app.models.default_account import DefaultAccount
from app.models.exchange_rate import ExchangeRate
from app.models.invoice import Invoice
from app.models.item import Item
from app.models.item_group import ItemGroup
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.payment_audit_log import PaymentAuditLog
from app.models.payment_entry import PaymentEntry
from app.models.payment_reference import PaymentReference
from app.models.quotation import Quotation, QuotationItem
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.serial_no import SerialNo
from app.models.status_transition import StatusTransition
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
