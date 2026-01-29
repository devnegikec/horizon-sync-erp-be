"""Main API v1 router"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    invitations,
    organizations,
    permissions,
    roles,
    users,
)

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/identity", tags=["Authentication"])

api_router.include_router(users.router, prefix="/identity", tags=["Users"])

api_router.include_router(
    organizations.router, prefix="/identity", tags=["Organizations"]
)

api_router.include_router(permissions.router, prefix="/identity", tags=["Permissions"])

api_router.include_router(roles.router, prefix="/identity", tags=["Roles"])

api_router.include_router(invitations.router, prefix="/identity", tags=["Invitations"])
