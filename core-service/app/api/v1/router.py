"""API v1 router configuration"""

from fastapi import APIRouter

from app.api.v1.endpoints import item_groups, items, warehouses

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(items.router, prefix="/items", tags=["Items"])
api_router.include_router(
    item_groups.router, prefix="/item-groups", tags=["Item Groups"]
)
api_router.include_router(warehouses.router, prefix="/warehouses", tags=["Warehouses"])
