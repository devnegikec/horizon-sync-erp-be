"""API v1 router configuration"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    chart_of_accounts,
    customers,
    item_groups,
    items,
    suppliers,
    warehouses,
)

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(items.router, prefix="/items", tags=["Items"])
api_router.include_router(
    item_groups.router, prefix="/item-groups", tags=["Item Groups"]
)
api_router.include_router(warehouses.router, prefix="/warehouses", tags=["Warehouses"])
api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["Suppliers"])
api_router.include_router(
    chart_of_accounts.router,
    prefix="/chart-of-accounts",
    tags=["Chart of Accounts"],
)
