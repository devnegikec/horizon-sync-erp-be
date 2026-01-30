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
