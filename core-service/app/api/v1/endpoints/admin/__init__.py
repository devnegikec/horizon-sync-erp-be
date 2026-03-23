"""
Admin portal endpoints package.

Exposes a combined `router` that includes:
- Dev/seed endpoints (seed-data, clear-data, health)
- Future admin portal sub-routers (dashboard, organizations, users, etc.)

The `router` attribute maintains backward compatibility with the existing
import in router.py: `from app.api.v1.endpoints import admin` / `admin.router`.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.admin.dashboard import router as dashboard_router
from app.api.v1.endpoints.admin.dev import router as dev_router
from app.api.v1.endpoints.admin.invoices import router as invoices_router
from app.api.v1.endpoints.admin.organizations import router as organizations_router
from app.api.v1.endpoints.admin.payments import router as payments_router
from app.api.v1.endpoints.admin.activity_logs import router as activity_logs_router
from app.api.v1.endpoints.admin.users import router as users_router

# Main admin router — all admin sub-routers are included here.
# This is the single router mounted at /admin in the main app router.
router = APIRouter()

# Include existing dev/seed endpoints at the admin root level
router.include_router(dev_router, tags=["Admin - Dev"])

# Dashboard
router.include_router(dashboard_router, prefix="/dashboard", tags=["Admin - Dashboard"])

# Organizations
router.include_router(organizations_router, prefix="/organizations", tags=["Admin - Organizations"])

# Users
router.include_router(users_router, prefix="/users", tags=["Admin - Users"])

# Invoices
router.include_router(invoices_router, prefix="/invoices", tags=["Admin - Invoices"])

# Payments
router.include_router(payments_router, prefix="/payments", tags=["Admin - Payments"])

# Activity Logs
router.include_router(activity_logs_router, prefix="/activity-logs", tags=["Admin - Activity Logs"])
