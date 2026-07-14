"""API v1 router configuration"""

from fastapi import APIRouter

from app.api.v1.endpoints import search
# Temporarily disabled until sync service is fully loaded
# from app.api.v1.endpoints import sync

# Create API v1 router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(search.router)
# api_router.include_router(sync.router)
