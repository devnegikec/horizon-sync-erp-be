"""Database models package"""

from app.models.account_audit_log import AccountAuditLog, AuditAction
from app.models.account_balance import AccountBalance

# Admin Portal module
from app.models.admin import (
    AdminAuditLog,
    AdminNotification,
    # FeatureFlag,
    UserActivityLog,
)

# Analytics module
from app.models.analytics import MetaCampaign
from app.models.asn_order import AsnOrder, AsnOrderItem

# Audit Trail module
from app.models.audit_log import AuditAction as AuditLogAction
from app.models.audit_log import AuditLog
from app.models.bank_account import BankAccount, BankAccountHistory
from app.models.bank_reconciliation import BankReconciliation
from app.models.bank_transaction import BankTransaction
from app.models.base import (
    AccountStatus,
    AccountType,
    AsnOrderStatus,
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
    NotificationType,
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
    WarehouseUserRole,
)
from app.models.batch import Batch
from app.models.bin_reservation import BinReservation
from app.models.bin_stock_level import BinStockLevel
from app.models.bulk_export_job import BulkExportJob
from app.models.bulk_import_job import BulkImportJob

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

# Bulk Import/Export module
# Campaigns & Coupons module
from app.models.campaign import Campaign, Play2WinPrize, WebCampaign
from app.models.charge_template import ChargeTemplate
from app.models.chart_of_account import Account

# Procurement / Sourcing / Fulfillment modules
from app.models.communication import CommunicationLog
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
from app.models.delivery_note import DeliveryNote, DeliveryNoteItem

# Destinations module
# Destinations module
from app.models.destination_market import DestinationMarket
from app.models.dispatch_record import DispatchRecord
from app.models.document_numbering import (
    DocumentNumberingConfig,
    DocumentSequenceCounter,
)
from app.models.exchange_rate import ExchangeRate

# Feature Flag module
from app.models.feature_flag import FeatureFlag
from app.models.gate_verification import GateVerificationItem, GateVerificationSession
from app.models.invoice import Invoice
from app.models.item import Item
from app.models.item_group import ItemGroup
from app.models.item_packaging_unit import ItemPackagingUnit
from app.models.item_price import ItemPrice
from app.models.item_supplier import ItemSupplier
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.landed_cost import LandedCostVoucher
from app.models.landing_page import LandingPageConfig
from app.models.location_allocation import LocationAllocation
from app.models.packaging_types import PackagingType
from app.models.location_scan import LocationScan
from app.models.material_request import MaterialRequest, MaterialRequestLine

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
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.payment_audit_log import PaymentAuditLog
from app.models.payment_entry import PaymentEntry
from app.models.payment_reference import PaymentReference
from app.models.pending_warehouse_assignment import PendingWarehouseAssignment
from app.models.pick_list import PickList, PickListItem
from app.models.product_item import ProductItem
from app.models.product_sku import ProductSKU
from app.models.products import Product

# Public Marketing module
# Public Marketing module
from app.models.public_submission import PublicSubmission
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.purchase_receipt import PurchaseReceipt, PurchaseReceiptItem
from app.models.put_away_list import PutAwayList, PutAwayListItem
from app.models.put_away_rule import PutAwayRule
from app.models.qr_activation import QRActivationParameters, QRActivationTrack
from app.models.qr_block import QRBlock
from app.models.qr_credit import (
    QRCreditBalance,
    QRCreditLedger,
    QRCreditReservation,
    QRCreditUsage,
)
from app.models.qr_cta_config import QRCTAConfig
from app.models.qr_product import QRProduct
from app.models.qr_product_setting import QRProductSetting
from app.models.qr_scan_event import QRScanEvent
from app.models.qr_scan_interaction import QRScanInteraction
from app.models.qseal import QSealParameters, QSealTrack
from app.models.quality_inspection import (
    QualityInspection,
    QualityInspectionParameter,
    QualityInspectionReading,
    QualityInspectionTemplate,
)
from app.models.quotation import Quotation, QuotationItem
from app.models.receiving_slip import ReceivingSlip, ReceivingSlipItem

# Reminder Configuration module (Task 1D-1)
from app.models.reminder_config import (
    ReminderConfig,
    ReminderLog,
    ReminderStage,
    ReminderStatus,
    ReminderType,
)
from app.models.rfq import RFQ, RFQLine, RFQSupplier, SupplierQuote
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.scan_session import ScanSession, ScanSessionItem
from app.models.scanned_item_tracking import ScannedItemTracking
from app.models.serial_no import SerialNo

# URL Management module
# URL Management module
from app.models.short_url import ShortURL
from app.models.sku_variant_attribute import (
    ProductSKUAttributeValue,
    VariantAttribute,
    VariantAttributeValue,
)
from app.models.status_transition import StatusTransition
from app.models.stock_entry import StockEntry, StockEntryItem
from app.models.stock_level import StockLevel
from app.models.stock_movement import StockMovement
from app.models.stock_reconciliation import StockReconciliation, StockReconciliationItem
from app.models.stock_settings import StockSettings
from app.models.supplier import Supplier
from app.models.system_config import SystemConfig
from app.models.tax_template import TaxRule, TaxTemplate
from app.models.transaction_breakdown import (
    TransactionChargeBreakdown,
    TransactionTaxBreakdown,
)
from app.models.uom import UOM
from app.models.uom_conversion import UOMConversion
from app.models.vehicle import Vehicle, VehicleArrival
from app.models.warehouse import Warehouse
from app.models.warehouse_floor_plan import WarehouseFloorPlan

# Warehouse Bin Management module
from app.models.warehouse_location import (
    AllocationType,
    GateVerificationItemStatus,
    GateVerificationStatus,
    LocationType,
    PutAwayListItemStatus,
    PutAwayListStatus,
    ReceivingSlipItemFlag,
    ReceivingSlipStatus,
    ScanSessionStatus,
    ScanSessionType,
    ScanType,
    WarehouseLocation,
    WorkerTaskStatus,
    WorkerTaskType,
)
from app.models.warehouse_user import WarehouseUser

# Warranty module
from app.models.warranty import Warranty, WarrantyPeriod
from app.models.wms_device import WMSDevice, WMSDeviceStatus
from app.models.wms_worker import WMSWorker, WMSWorkerStatus
from app.models.worker_task import WorkerTask

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
    "AsnOrderStatus",
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
    "ItemPackagingUnit",
    "PackagingType",
    "JournalEntry",
    "JournalEntryLine",
    "PaymentEntry",
    "PaymentReference",
    "PaymentAuditLog",
    "BulkExportJob",
    "BulkImportJob",
    "PendingWarehouseAssignment",
    "PickList",
    "PickListItem",
    "AsnOrder",
    "AsnOrderItem",
    "Vehicle",
    "VehicleArrival",
    "Quotation",
    "QuotationItem",
    "SalesOrder",
    "SalesOrderItem",
    "SystemConfig",
    "Warehouse",
    "Customer",
    "Supplier",
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
    "QRProductSetting",
    "QRBlock",
    "ProductItem",
    "ProductSKU",
    "Product",
    "VariantAttribute",
    "VariantAttributeValue",
    "ProductSKUAttributeValue",
    "QRActivationParameters",
    "QRActivationTrack",
    "QSealParameters",
    "QSealTrack",
    "QRCreditUsage",
    "QRCreditBalance",
    "QRCreditReservation",
    "QRCreditLedger",
    "QRCTAConfig",
    "LandingPageConfig",
    "QRScanEvent",
    "QRScanInteraction",
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
    # WMS / Notification module
    "Notification",
    "NotificationType",
    "WarehouseUser",
    "WarehouseUserRole",
    "WMSWorker",
    "WMSWorkerStatus",
    "WMSDevice",
    "WMSDeviceStatus",
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
    "ScanSessionType",
    "ScanSessionStatus",
    "ReceivingSlipStatus",
    "ReceivingSlipItemFlag",
    "GateVerificationStatus",
    "GateVerificationItemStatus",
    "WarehouseLocation",
    "WarehouseFloorPlan",
    "BinStockLevel",
    "BinReservation",
    "LocationAllocation",
    "ScanSession",
    "ScanSessionItem",
    "ReceivingSlip",
    "ReceivingSlipItem",
    "GateVerificationSession",
    "GateVerificationItem",
    "DispatchRecord",
    "WorkerTask",
    "LocationScan",
    "PutAwayList",
    "PutAwayListItem",
    # Procurement / Sourcing / Fulfillment modules
    "CommunicationLog",
    "DeliveryNote",
    "DeliveryNoteItem",
    "DocumentNumberingConfig",
    "DocumentSequenceCounter",
    "ItemPrice",
    "ItemSupplier",
    "LandedCostVoucher",
    "MaterialRequest",
    "MaterialRequestLine",
    "Payment",
    "PurchaseOrder",
    "PurchaseOrderLine",
    "PurchaseReceipt",
    "PurchaseReceiptItem",
    "PutAwayRule",
    "QualityInspection",
    "QualityInspectionParameter",
    "QualityInspectionReading",
    "QualityInspectionTemplate",
    "RFQ",
    "RFQLine",
    "RFQSupplier",
    "SupplierQuote",
    "StatusTransition",
    "StockSettings",
]
