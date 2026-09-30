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
ITEM_MANAGE = "item.manage"
ITEM_GROUP_READ = "item_group.read"
ITEM_GROUP_CREATE = "item_group.create"
ITEM_GROUP_UPDATE = "item_group.update"
ITEM_GROUP_DELETE = "item_group.delete"
ITEM_GROUP_MANAGE = "item_group.manage"

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
BATCH_UPDATE = "batch.update"
BATCH_DELETE = "batch.delete"
BATCH_MANAGE = "batch.manage"
SERIAL_READ = "serial.read"
SERIAL_CREATE = "serial.create"
SERIAL_UPDATE = "serial.update"
SERIAL_DELETE = "serial.delete"
SERIAL_MANAGE = "serial.manage"
# Legacy aliases — the canonical resource is "serial", not "serial_no".
SERIAL_NO_READ = SERIAL_READ
SERIAL_NO_CREATE = SERIAL_CREATE
STOCK_LEVEL_READ = "stock_level.read"
STOCK_LEVEL_CREATE = "stock_level.create"
STOCK_LEVEL_UPDATE = "stock_level.update"
STOCK_RECONCILIATION_READ = "stock_reconciliation.read"
STOCK_RECONCILIATION_CREATE = "stock_reconciliation.create"
STOCK_RECONCILIATION_UPDATE = "stock_reconciliation.update"
STOCK_RECONCILIATION_DELETE = "stock_reconciliation.delete"
STOCK_SETTINGS_READ = "stock_settings.read"
STOCK_SETTINGS_UPDATE = "stock_settings.update"
PUT_AWAY_RULE_READ = "put_away_rule.read"
PUT_AWAY_RULE_CREATE = "put_away_rule.create"
PUT_AWAY_RULE_UPDATE = "put_away_rule.update"
PUT_AWAY_RULE_DELETE = "put_away_rule.delete"

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
PAYMENT_UPDATE = "payment.update"
PAYMENT_DELETE = "payment.delete"
PAYMENT_MANAGE = "payment.manage"
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

# Procurement
PURCHASE_ORDER_READ = "purchase_order.read"
PURCHASE_ORDER_CREATE = "purchase_order.create"
PURCHASE_ORDER_UPDATE = "purchase_order.update"
PURCHASE_ORDER_DELETE = "purchase_order.delete"
PURCHASE_ORDER_MANAGE = "purchase_order.manage"

# Settings / Reporting
SETTING_READ = "setting.read"
SETTING_UPDATE = "setting.update"
SETTING_MANAGE = "setting.manage"
REPORT_READ = "report.read"

# Analytics (module is additionally gated by the analytics feature flag)
ANALYTICS_READ = "analytics.read"
ANALYTICS_CREATE = "analytics.create"
ANALYTICS_UPDATE = "analytics.update"
ANALYTICS_DELETE = "analytics.delete"

# Banking
BANK_ACCOUNT_READ = "bank_account.read"
BANK_ACCOUNT_CREATE = "bank_account.create"
BANK_ACCOUNT_UPDATE = "bank_account.update"
BANK_ACCOUNT_DELETE = "bank_account.delete"
BANK_ACCOUNT_MANAGE = "bank_account.manage"
RECONCILIATION_READ = "reconciliation.read"
RECONCILIATION_CREATE = "reconciliation.create"
RECONCILIATION_UPDATE = "reconciliation.update"
RECONCILIATION_DELETE = "reconciliation.delete"

# QSeal / QR marketing & verification
QSEAL_READ = "qseal.read"
QSEAL_CREATE = "qseal.create"
QSEAL_UPDATE = "qseal.update"
QSEAL_DELETE = "qseal.delete"
QSEAL_MANAGE = "qseal.manage"
LANDING_PAGE_READ = "landing_page.read"
LANDING_PAGE_CREATE = "landing_page.create"
LANDING_PAGE_UPDATE = "landing_page.update"
LANDING_PAGE_DELETE = "landing_page.delete"
LANDING_PAGE_MANAGE = "landing_page.manage"

# Messaging / Communications
MESSAGING_READ = "messaging.read"
MESSAGING_CREATE = "messaging.create"
MESSAGING_UPDATE = "messaging.update"
MESSAGING_DELETE = "messaging.delete"
MESSAGING_SEND = "messaging.send"
COMMUNICATION_READ = "communication.read"
COMMUNICATION_CREATE = "communication.create"
COMMUNICATION_UPDATE = "communication.update"
COMMUNICATION_DELETE = "communication.delete"
COMMUNICATION_SEND = "communication.send"
BRAND_TRUST_READ = "brand_trust.read"
BRAND_TRUST_CREATE = "brand_trust.create"
BRAND_TRUST_UPDATE = "brand_trust.update"

# Bulk import / export
BULK_EXPORT_READ = "bulk_export.read"
BULK_EXPORT_CREATE = "bulk_export.create"
BULK_IMPORT_CREATE = "bulk_import.create"
BULK_IMPORT_READ = "bulk_import.read"

# Tax & charges templates
CHARGE_TEMPLATE_READ = "charge_template.read"
CHARGE_TEMPLATE_CREATE = "charge_template.create"
CHARGE_TEMPLATE_UPDATE = "charge_template.update"
CHARGE_TEMPLATE_DELETE = "charge_template.delete"

# Short URLs (admin management; resolution is public)
SHORT_URL_READ = "short_url.read"
SHORT_URL_CREATE = "short_url.create"
SHORT_URL_UPDATE = "short_url.update"
SHORT_URL_DELETE = "short_url.delete"

# Document numbering
DOCUMENT_NUMBERING_READ = "document_numbering.read"
DOCUMENT_NUMBERING_UPDATE = "document_numbering.update"

# Pick settings
PICK_SETTING_READ = "pick_setting.read"
PICK_SETTING_UPDATE = "pick_setting.update"

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

# Returns (customer returns) module — R-10 / X-02.
# ``return.receive`` and ``return.classify`` are dock (handheld) duties;
# ``return.register`` is back-office and ``return.approve`` / ``return.dispose``
# additionally require warehouse-manager authority at the warehouse level.
RETURN_READ = "return.read"
RETURN_REGISTER = "return.register"
RETURN_RECEIVE = "return.receive"
RETURN_CLASSIFY = "return.classify"
RETURN_APPROVE = "return.approve"
RETURN_DISPOSE = "return.dispose"

# QR scanning (Inbound + Outbound)
WMS_SCAN = "wms.scan"

# Warehouse worker/device management (Admin/Owner/WMS Supervisor/WMS Manager)
WAREHOUSE_MANAGE = "warehouse.manage"

# Fixed permission set embedded in a WMS worker's barcode-login token.
# Workers are API-only mobile clients: they scan QR codes and create/update
# receiving slips (Inbound), read/update pick lists (Outbound), and read ASN
# orders. They can NOT create pick lists, manage workers/devices, edit
# warehouse records, or access anything else.
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
    # Returns: the dock may receive and classify returned units, never approve.
    RETURN_READ,
    RETURN_RECEIVE,
    RETURN_CLASSIFY,
]


def is_worker_scope(user_type: str, permissions: list[str]) -> bool:
    """True when the caller is a warehouse worker rather than a manager/admin.

    Workers (mobile/PDA scanner users) must only see the put-away and pick
    lists assigned to them. Warehouse managers, supervisors, org/system admins,
    and anyone holding the full wildcard keep the organization-wide view.
    """
    if user_type in ("system_admin", "organization_admin"):
        return False
    if "*.*" in permissions:
        return False
    return WAREHOUSE_MANAGE not in permissions


def has_global_warehouse_access(user_type: str, permissions: list[str]) -> bool:
    """True when the caller may see every warehouse in the organization.

    Only system/organization admins and holders of the full wildcard get an
    unconditional organization-wide warehouse view.

    ``warehouse.manage`` deliberately does NOT imply global visibility. WMS
    Managers are granted it for worker/device CRUD but remain scoped to their
    ``WarehouseUser`` assignments. Callers that must keep unassigned warehouse
    administrators working (e.g. a WMS Admin that was never scoped to specific
    warehouses) should apply their own explicit fallback — see
    ``WarehouseUserService.get_user_warehouses``.
    """
    if user_type in ("system_admin", "organization_admin"):
        return True
    return "*.*" in permissions
