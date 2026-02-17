"""Database models package"""

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
    PaymentMethod,
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
)
from app.models.chart_of_account import Account
from app.models.account_balance import AccountBalance
from app.models.customer import Customer
from app.models.exchange_rate import ExchangeRate
from app.models.item import Item
from app.models.item_group import ItemGroup
from app.models.quotation import Quotation, QuotationItem
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.system_config import SystemConfig
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
    # Models
    "Account",
    "AccountBalance",
    "Customer",
    "ExchangeRate",
    "Item",
    "ItemGroup",
    "Quotation",
    "QuotationItem",
    "SalesOrder",
    "SalesOrderItem",
    "SystemConfig",
    "Warehouse",
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
