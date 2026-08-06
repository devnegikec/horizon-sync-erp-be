"""API v1 router configuration"""

from fastapi import APIRouter

# from app.api.v1.endpoints import item_groups, item_prices, items, warehouses
from app.api.v1.endpoints import (
    admin,
    analytics,
    asn_orders,
    bank_accounts,
    batches,
    bin_stock,
    brand_trust,
    brands,
    bulk_export,
    bulk_import,
    campaigns,
    charge_templates,
    cascade,
    chart_of_accounts,
    chart_of_accounts_setup,
    communications,
    currencies,
    currency,
    customer_bulk,
    customers,
    delivery_notes,
    destinations,
    document_numbering,
    exchange_rates,
    feature_flag_evaluate,
    floor_plans,
    inbound,
    internal_warehouse_users,
    invoices,
    item_groups,
    item_packaging_units,
    item_prices,
    items,
    items_picker,
    journal_entries,
    landed_cost,
    landing_pages,
    location_allocations,
    location_scans,
    material_requests,
    messaging,
    notifications,
    organization_onboarding,
    outbound,
    payments,
    pick_lists,
    public_marketing,
    public_qr,
    purchase_orders,
    purchase_receipts,
    put_away,
    put_away_rules,
    qr_credits,
    qr_activation,
    qr_product_settings,
    qr_products,
    quality_inspections,
    quotations,
    reconciliations,
    rfqs,
    sales_orders,
    scan_events,
    serial_numbers,
    short_urls,
    sku_endpoint,
    smart_picking,
    stock_entries,
    stock_entry_bulk_import,
    stock_levels,
    stock_movements,
    stock_reconciliations,
    stock_settings,
    suppliers,
    tax_templates,
    uom_conversions,
    uoms,
    warehouse_locations,
    warehouse_users,
    warehouses,
    warranties,
    wms_3d,
    wms_dashboard,
    wms_devices,
    worker_tasks,
)

api_router = APIRouter()

# Admin endpoints (development only)
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])

# Feature flag evaluation (any authenticated user)
api_router.include_router(
    feature_flag_evaluate.router,
    prefix="/feature-flags",
    tags=["Feature Flags"],
)

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
# Item Packaging Units — nested under /items/{item_id}/packaging-units
api_router.include_router(
    item_packaging_units.router,
    prefix="/items/{item_id}/packaging-units",
    tags=["Item Packaging Units"],
)
# Bulk Operations
api_router.include_router(bulk_import.router)
api_router.include_router(bulk_export.router)
api_router.include_router(warehouses.router, prefix="/warehouses", tags=["Warehouses"])
api_router.include_router(
    warehouse_locations.router,
    prefix="/warehouse-locations",
    tags=["Warehouse Locations"],
)
api_router.include_router(
    warehouse_users.router,
    prefix="/warehouse-users",
    tags=["Warehouse Users"],
)
api_router.include_router(
    bin_stock.router,
    prefix="/bin-stock",
    tags=["Bin Stock"],
)
api_router.include_router(
    floor_plans.router,
    prefix="/floor-plans",
    tags=["Floor Plan Designer"],
)
api_router.include_router(
    wms_3d.router,
    prefix="/wms-3d",
    tags=["WMS 3D View"],
)
api_router.include_router(
    wms_devices.router,
    prefix="/wms-devices",
    tags=["WMS Devices"],
)
api_router.include_router(
    wms_dashboard.router,
    prefix="/wms-dashboard",
    tags=["WMS Dashboard"],
)
api_router.include_router(
    location_allocations.router,
    prefix="/location-allocations",
    tags=["Location Allocations"],
)
# Inbound (scan sessions, receiving slips)
api_router.include_router(
    inbound.router,
    prefix="/inbound",
    tags=["Inbound"],
)
# Outbound (SAP invoice-triggered pick lists)
api_router.include_router(
    outbound.router,
    prefix="/outbound",
    tags=["Outbound"],
)
# Put-Away (put-away lists and items)
api_router.include_router(
    put_away.router,
    prefix="/put-away",
    tags=["Put Away"],
)
# Worker Tasks (put-away and pick task assignments)
api_router.include_router(
    worker_tasks.router,
    prefix="/worker-tasks",
    tags=["Worker Tasks"],
)
# Location Scans (QR-based time tracking)
api_router.include_router(
    location_scans.router,
    prefix="/location-scans",
    tags=["Location Scans"],
)
# Scan Events (QR scan audit trail)
api_router.include_router(
    scan_events.router,
    prefix="/scan-events",
    tags=["Scan Events"],
)
api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
api_router.include_router(customer_bulk.router)
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["Suppliers"])
api_router.include_router(
    chart_of_accounts.router,
    prefix="/chart-of-accounts",
    tags=["Chart of Accounts"],
)
# Chart of Accounts Setup
api_router.include_router(
    chart_of_accounts_setup.router,
    prefix="",  # No prefix since endpoints already include /setup
    tags=["Chart of Accounts Setup"],
)
# Organization Onboarding (seed defaults for new orgs)
api_router.include_router(
    organization_onboarding.router,
    prefix="",  # No prefix since endpoint already includes /setup
    tags=["Organization Setup"],
)
# Internal Warehouse Users (service-to-service, no auth)
api_router.include_router(
    internal_warehouse_users.router,
    prefix="",  # No prefix since endpoint already includes /internal
    tags=["Internal"],
)
# Bank accounts integration
api_router.include_router(
    bank_accounts.router,
    prefix="",  # No prefix since endpoints are already properly prefixed
    tags=["Bank Accounts"],
)
# Also register with /accounts prefix for config endpoints
api_router.include_router(
    chart_of_accounts.router,
    prefix="/accounts",
    tags=["Accounts"],
)
# Bank Accounts for banking integration
api_router.include_router(
    bank_accounts.router,
    prefix="",
    tags=["Bank Accounts"],
)
# Bank Reconciliations
api_router.include_router(
    reconciliations.router,
    prefix="/reconciliations",
    tags=["Bank Reconciliations"],
)
api_router.include_router(currency.router, prefix="/currency", tags=["Currency"])
# UOM & Currency Master
api_router.include_router(uoms.router, prefix="/uoms", tags=["UOMs"])
api_router.include_router(
    uom_conversions.router, prefix="/uom-conversions", tags=["UOM Conversions"]
)
api_router.include_router(currencies.router, prefix="/currencies", tags=["Currencies"])
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
    stock_entry_bulk_import.router,
    prefix="/stock-entries/bulk",
    tags=["Stock Entries"],
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
api_router.include_router(asn_orders.router, prefix="/asn-orders", tags=["ASN Orders"])
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
    charge_templates.router,
    prefix="/charge-templates",
    tags=["Charge Templates"],
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

# QR Credits module (balance & usage)
api_router.include_router(
    qr_credits.router,
    prefix="/qr-credits",
    tags=["QR Credits"],
)

# QR Products module
api_router.include_router(
    qr_products.router,
    prefix="/qr-products",
    tags=["QR Products"],
)

# SKU Management module
api_router.include_router(
    sku_endpoint.router,
    prefix="/sku",
    tags=["SKU Management"],
)

# Landing Page Config (nested under /products/{productId}/landing-page)
api_router.include_router(
    landing_pages.router,
    prefix="/products",
    tags=["Landing Pages"],
)

# Public Landing Page Config (no auth — for consumer QR verification pages)
api_router.include_router(
    landing_pages.public_router,
    prefix="/public/products",
    tags=["Landing Pages (Public)"],
)

# QR Product Settings (serial prefix, channel, destination, shelf life)
api_router.include_router(
    qr_product_settings.router,
    prefix="/qr-product-settings",
    tags=["QR Product Settings"],
)

# Campaigns & Coupons module
api_router.include_router(
    campaigns.router,
    prefix="/campaigns",
    tags=["Campaigns"],
)

# Warranty module
api_router.include_router(
    warranties.router,
    prefix="/warranties",
    tags=["Warranties"],
)

# Messaging module
api_router.include_router(
    messaging.router,
    prefix="/messaging",
    tags=["Messaging"],
)

# Notifications module (WMS/ASN in-app notifications)
api_router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["Notifications"],
)

# Analytics module
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"],
)

# URL Management module
api_router.include_router(
    short_urls.router,
    prefix="/short-urls",
    tags=["URL Management"],
)

# Destinations module
api_router.include_router(
    destinations.router,
    prefix="/destinations",
    tags=["Destinations"],
)

# Brand Trust Assessment module
api_router.include_router(
    brand_trust.router,
    prefix="/brand-trust",
    tags=["Brand Trust"],
)

# Brands module (ECDSA key pair management)
api_router.include_router(
    brands.router,
    prefix="/brands",
    tags=["Brands"],
)

# Public / Marketing module (no auth)
api_router.include_router(
    public_marketing.router,
    prefix="/public",
    tags=["Public"],
)

api_router.include_router(
    public_qr.router,
    prefix="/public/qr",
    tags=["Public QR Verification"],
)


# QR Activation module 
api_router.include_router(
    qr_activation.router,
    prefix="/qr-activation",
    tags=["QR Activation"],
)

api_router.include_router(cascade.router, prefix="/cascade", tags=["Cascade"])
