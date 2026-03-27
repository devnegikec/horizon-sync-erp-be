"""Main API v1 router"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    invitations,
    organizations,
    otp,
    permissions,
    roles,
    users,
    organization_deactivation,
)
from app.api.v1.endpoints.admin import auth as admin_auth

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

api_router.include_router(otp.router, prefix="/identity", tags=["OTP"])

api_router.include_router(
    admin_auth.router, prefix="/identity/admin", tags=["Admin Auth"]
)

api_router.include_router(
    organization_deactivation.router, prefix="/organization-management", tags=["Organization Management"]
)
