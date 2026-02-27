"""API v1 router configuration"""

from fastapi import APIRouter

# from app.api.v1.endpoints import item_groups, item_prices, items, warehouses
from app.api.v1.endpoints import (
    admin,
    batches,
    bulk_export,
    bulk_import,
    chart_of_accounts,
    communications,
    currencies,
    currency,
    customers,
    delivery_notes,
    document_numbering,
    exchange_rates,
    invoices,
    item_groups,
    item_prices,
    items,
    items_picker,
    journal_entries,
    landed_cost,
    material_requests,
    payments,
    pick_lists,
    purchase_orders,
    purchase_receipts,
    put_away_rules,
    quality_inspections,
    quotations,
    rfqs,
    sales_orders,
    serial_numbers,
    smart_picking,
    stock_entries,
    stock_levels,
    stock_movements,
    stock_reconciliations,
    stock_settings,
    suppliers,
    tax_templates,
    uom_conversions,
    uoms,
    warehouses,
)

api_router = APIRouter()

# Admin endpoints (development only)
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])

# Include endpoint routers
# Item picker MUST be before items router so /items/picker matches before /items/{item_id}
api_router.include_router(items_picker.router, prefix="/items/picker", tags=["Items"])
api_router.include_router(items.router, prefix="/items", tags=["Items"])
api_router.include_router(
    item_groups.router, prefix="/item-groups", tags=["Item Groups"]
)
api_router.include_router(
    item_prices.router, prefix="/item-prices", tags=["Item Prices"]
)
# Bulk Operations
api_router.include_router(bulk_import.router)
api_router.include_router(bulk_export.router)
api_router.include_router(warehouses.router, prefix="/warehouses", tags=["Warehouses"])
api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["Suppliers"])
api_router.include_router(
    chart_of_accounts.router,
    prefix="/chart-of-accounts",
    tags=["Chart of Accounts"],
)
# Also register with /accounts prefix for config endpoints
api_router.include_router(
    chart_of_accounts.router,
    prefix="/accounts",
    tags=["Accounts"],
)
api_router.include_router(currency.router, prefix="/currency", tags=["Currency"])
# UOM & Currency Master
api_router.include_router(uoms.router, prefix="/uoms", tags=["UOMs"])
api_router.include_router(
    uom_conversions.router, prefix="/uom-conversions", tags=["UOM Conversions"]
)
api_router.include_router(
    currencies.router, prefix="/currencies", tags=["Currencies"]
)
api_router.include_router(
    exchange_rates.router, prefix="/exchange-rates", tags=["Exchange Rates"]
)
# Phase 3: Stock Management
api_router.include_router(batches.router, prefix="/batches", tags=["Batches"])
api_router.include_router(
    serial_numbers.router, prefix="/serial-numbers", tags=["Serial Numbers"]
)
api_router.include_router(
    stock_entries.router, prefix="/stock-entries", tags=["Stock Entries"]
)
api_router.include_router(
    stock_levels.router, prefix="/stock-levels", tags=["Stock Levels"]
)
api_router.include_router(
    stock_movements.router, prefix="/stock-movements", tags=["Stock Movements"]
)
api_router.include_router(
    stock_reconciliations.router,
    prefix="/stock-reconciliations",
    tags=["Stock Reconciliations"],
)
api_router.include_router(
    stock_settings.router, prefix="/stock-settings", tags=["Stock Settings"]
)
api_router.include_router(
    put_away_rules.router, prefix="/put-away-rules", tags=["Put Away Rules"]
)
# Phase 4: Quality Management
api_router.include_router(
    quality_inspections.router,
    prefix="/quality-inspections",
    tags=["Quality Inspections"],
)
# Phase 5: Order Processing
api_router.include_router(pick_lists.router, prefix="/pick-lists", tags=["Pick Lists"])
api_router.include_router(
    delivery_notes.router, prefix="/delivery-notes", tags=["Delivery Notes"]
)
api_router.include_router(
    purchase_receipts.router, prefix="/purchase-receipts", tags=["Purchase Receipts"]
)
# Phase 6: Landed Cost
api_router.include_router(
    landed_cost.router, prefix="/landed-cost", tags=["Landed Cost"]
)
# Phase 7: Billing
api_router.include_router(invoices.router, prefix="/invoices", tags=["Invoices"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(
    journal_entries.router, prefix="/journal-entries", tags=["Journal Entries"]
)
# Quotation and Sales Order
api_router.include_router(quotations.router, prefix="/quotations", tags=["Quotations"])
api_router.include_router(
    sales_orders.router, prefix="/sales-orders", tags=["Sales Orders"]
)
# Sourcing Flow
api_router.include_router(
    material_requests.router,
    prefix="/material-requests",
    tags=["Material Requests"],
)
api_router.include_router(
    rfqs.router,
    prefix="/rfqs",
    tags=["RFQs"],
)
# Tax and Charges
api_router.include_router(
    tax_templates.router,
    prefix="/tax-templates",
    tags=["Tax Templates"],
)
api_router.include_router(
    purchase_orders.router,
    prefix="/purchase-orders",
    tags=["Purchase Orders"],
)
# Communications
api_router.include_router(
    communications.router,
    prefix="/communications",
    tags=["Communications"],
)
# Smart Picking
api_router.include_router(
    smart_picking.router,
    prefix="/smart-picking",
    tags=["Smart Picking"],
)
# Settings: Document Numbering Series
api_router.include_router(
    document_numbering.router,
    prefix="/settings/document-numbering",
    tags=["Settings - Document Numbering"],
)
