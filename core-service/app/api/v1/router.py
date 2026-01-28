"""API v1 router configuration"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    batches,
    chart_of_accounts,
    customers,
    item_groups,
    item_prices,
    item_suppliers,
    items,
    put_away_rules,
    serial_numbers,
    stock_entries,
    stock_levels,
    stock_movements,
    stock_reconciliations,
    stock_settings,
    suppliers,
    warehouses,
)

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(items.router, prefix="/items", tags=["Items"])
api_router.include_router(
    item_groups.router, prefix="/item-groups", tags=["Item Groups"]
)
api_router.include_router(
    item_prices.router, prefix="/item-prices", tags=["Item Prices"]
)
api_router.include_router(
    item_suppliers.router, prefix="/item-suppliers", tags=["Item Suppliers"]
)
api_router.include_router(warehouses.router, prefix="/warehouses", tags=["Warehouses"])
api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["Suppliers"])
api_router.include_router(
    chart_of_accounts.router,
    prefix="/chart-of-accounts",
    tags=["Chart of Accounts"],
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
