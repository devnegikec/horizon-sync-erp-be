"""
RBAC permission codes for core-service APIs.

These must match permissions defined in identity-service (permissions table)
and assigned to roles. Format: resource.action (e.g. warehouse.read).
"""

# Warehouse
WAREHOUSE_READ = "warehouse.read"
WAREHOUSE_CREATE = "warehouse.create"
WAREHOUSE_UPDATE = "warehouse.update"
WAREHOUSE_DELETE = "warehouse.delete"

# Item, Item Group, Item Price, Item Supplier
ITEM_READ = "item.read"
ITEM_CREATE = "item.create"
ITEM_UPDATE = "item.update"
ITEM_DELETE = "item.delete"

# Master data
CUSTOMER_READ = "customer.read"
CUSTOMER_CREATE = "customer.create"
CUSTOMER_UPDATE = "customer.update"
CUSTOMER_DELETE = "customer.delete"
SUPPLIER_READ = "supplier.read"
SUPPLIER_CREATE = "supplier.create"
SUPPLIER_UPDATE = "supplier.update"
SUPPLIER_DELETE = "supplier.delete"
CHART_OF_ACCOUNT_READ = "chart_of_account.read"
CHART_OF_ACCOUNT_CREATE = "chart_of_account.create"
CHART_OF_ACCOUNT_UPDATE = "chart_of_account.update"
CHART_OF_ACCOUNT_DELETE = "chart_of_account.delete"

# Stock
STOCK_ENTRY_READ = "stock_entry.read"
STOCK_ENTRY_CREATE = "stock_entry.create"
STOCK_ENTRY_UPDATE = "stock_entry.update"
STOCK_ENTRY_DELETE = "stock_entry.delete"
BATCH_READ = "batch.read"
BATCH_CREATE = "batch.create"
SERIAL_NO_READ = "serial_no.read"
SERIAL_NO_CREATE = "serial_no.create"
STOCK_LEVEL_READ = "stock_level.read"
STOCK_RECONCILIATION_READ = "stock_reconciliation.read"
STOCK_RECONCILIATION_CREATE = "stock_reconciliation.create"
STOCK_SETTINGS_READ = "stock_settings.read"
STOCK_SETTINGS_UPDATE = "stock_settings.update"
PUT_AWAY_RULE_READ = "put_away_rule.read"
PUT_AWAY_RULE_CREATE = "put_away_rule.create"

# Phase 4: Quality
QUALITY_INSPECTION_READ = "quality_inspection.read"
QUALITY_INSPECTION_CREATE = "quality_inspection.create"
QUALITY_INSPECTION_UPDATE = "quality_inspection.update"
QUALITY_INSPECTION_DELETE = "quality_inspection.delete"

# Phase 5: Order processing
PICK_LIST_READ = "pick_list.read"
PICK_LIST_CREATE = "pick_list.create"
PICK_LIST_UPDATE = "pick_list.update"
DELIVERY_NOTE_READ = "delivery_note.read"
DELIVERY_NOTE_CREATE = "delivery_note.create"
DELIVERY_NOTE_UPDATE = "delivery_note.update"
PURCHASE_RECEIPT_READ = "purchase_receipt.read"
PURCHASE_RECEIPT_CREATE = "purchase_receipt.create"
PURCHASE_RECEIPT_UPDATE = "purchase_receipt.update"

# Phase 6: Landed cost
LANDED_COST_READ = "landed_cost.read"
LANDED_COST_CREATE = "landed_cost.create"
LANDED_COST_UPDATE = "landed_cost.update"

# Phase 7: Billing
INVOICE_READ = "invoice.read"
INVOICE_CREATE = "invoice.create"
INVOICE_UPDATE = "invoice.update"
PAYMENT_READ = "payment.read"
PAYMENT_CREATE = "payment.create"
JOURNAL_ENTRY_READ = "journal_entry.read"
JOURNAL_ENTRY_CREATE = "journal_entry.create"
JOURNAL_ENTRY_UPDATE = "journal_entry.update"

# Quotation and Sales Order
QUOTATION_READ = "quotation.read"
QUOTATION_CREATE = "quotation.create"
QUOTATION_UPDATE = "quotation.update"
SALES_ORDER_READ = "sales_order.read"
SALES_ORDER_CREATE = "sales_order.create"
SALES_ORDER_UPDATE = "sales_order.update"

# Advance Stock Notice (ASN)
ASN_ORDER_READ = "asn_order.read"
ASN_ORDER_CREATE = "asn_order.create"
ASN_ORDER_UPDATE = "asn_order.update"

# UOM
UOM_READ = "uom.read"
UOM_CREATE = "uom.create"
UOM_UPDATE = "uom.update"
UOM_DELETE = "uom.delete"


# Currency
CURRENCY_READ = "currency.read"
CURRENCY_CREATE = "currency.create"
CURRENCY_UPDATE = "currency.update"
CURRENCY_DELETE = "currency.delete"


# Exchange Rate
EXCHANGE_RATE_READ = "exchange_rate.read"
EXCHANGE_RATE_CREATE = "exchange_rate.create"
EXCHANGE_RATE_UPDATE = "exchange_rate.update"
EXCHANGE_RATE_DELETE = "exchange_rate.delete"

# Audit
AUDIT_READ = "audit.read"

# System Admin — Users domain
SYSTEM_ADMIN_USERS_READ = "system_admin.users_read"
SYSTEM_ADMIN_USERS_CREATE = "system_admin.users_create"
SYSTEM_ADMIN_USERS_UPDATE = "system_admin.users_update"
SYSTEM_ADMIN_USERS_DELETE = "system_admin.users_delete"
SYSTEM_ADMIN_USERS_MANAGE = "system_admin.users_manage"

# System Admin — Organizations domain
SYSTEM_ADMIN_ORGANIZATIONS_READ = "system_admin.organizations_read"
SYSTEM_ADMIN_ORGANIZATIONS_CREATE = "system_admin.organizations_create"
SYSTEM_ADMIN_ORGANIZATIONS_UPDATE = "system_admin.organizations_update"
SYSTEM_ADMIN_ORGANIZATIONS_DELETE = "system_admin.organizations_delete"
SYSTEM_ADMIN_ORGANIZATIONS_MANAGE = "system_admin.organizations_manage"

# System Admin — Billing domain
SYSTEM_ADMIN_BILLING_READ = "system_admin.billing_read"
SYSTEM_ADMIN_BILLING_CREATE = "system_admin.billing_create"
SYSTEM_ADMIN_BILLING_UPDATE = "system_admin.billing_update"
SYSTEM_ADMIN_BILLING_DELETE = "system_admin.billing_delete"
SYSTEM_ADMIN_BILLING_MANAGE = "system_admin.billing_manage"

# System Admin — Reporting domain
SYSTEM_ADMIN_REPORTING_READ = "system_admin.reporting_read"
SYSTEM_ADMIN_REPORTING_CREATE = "system_admin.reporting_create"
SYSTEM_ADMIN_REPORTING_UPDATE = "system_admin.reporting_update"
SYSTEM_ADMIN_REPORTING_DELETE = "system_admin.reporting_delete"
SYSTEM_ADMIN_REPORTING_MANAGE = "system_admin.reporting_manage"

# System Admin — Master (super permission)
SYSTEM_ADMIN_MASTER = "system_admin.master"

# ============================================
# WMS WORKER (mobile/PDA scanner) PERMISSIONS
# ============================================
# Receiving slips (Inbound)
RECEIVING_SLIP_CREATE = "receiving_slip.create"
RECEIVING_SLIP_READ = "receiving_slip.read"
RECEIVING_SLIP_UPDATE = "receiving_slip.update"

# Inbound exception & hold/quarantine workflow. Classification is delegated
# through feature permissions; final disposition also requires warehouse-manager
# authority at the warehouse level.
INBOUND_EXCEPTION_READ = "inbound_exception.read"
INBOUND_EXCEPTION_CREATE = "inbound_exception.create"
INBOUND_EXCEPTION_DISPOSE = "inbound_exception.dispose"

# QR scanning (Inbound + Outbound)
WMS_SCAN = "wms.scan"

# Warehouse worker/device management (Admin/Owner/WMS Supervisor/WMS Manager)
WAREHOUSE_MANAGE = "warehouse.manage"

# Fixed permission set embedded in a WMS worker's barcode-login token.
# Workers are API-only mobile clients: they scan QR codes and create/update
# receiving slips (Inbound), read/update pick lists (Outbound), read ASN orders,
# and execute put-away. They can NOT create pick lists, manage workers/devices,
# or access anything else.
WMS_WORKER_PERMISSIONS = [
    WMS_SCAN,
    WAREHOUSE_READ,
    RECEIVING_SLIP_CREATE,
    RECEIVING_SLIP_READ,
    RECEIVING_SLIP_UPDATE,
    INBOUND_EXCEPTION_READ,
    INBOUND_EXCEPTION_CREATE,
    PICK_LIST_READ,
    PICK_LIST_UPDATE,
    ASN_ORDER_READ,
    STOCK_ENTRY_CREATE,
    STOCK_ENTRY_READ,
]
