"""
Admin portal endpoints package.

Exposes a combined `router` that includes:
- Dev/seed endpoints (seed-data, clear-data, health)
- Future admin portal sub-routers (dashboard, organizations, users, etc.)

The `router` attribute maintains backward compatibility with the existing
import in router.py: `from app.api.v1.endpoints import admin` / `admin.router`.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.admin.activity_logs import router as activity_logs_router
from app.api.v1.endpoints.admin.audit_logs import router as audit_logs_router
from app.api.v1.endpoints.admin.billing import router as billing_router
from app.api.v1.endpoints.admin.dashboard import router as dashboard_router
from app.api.v1.endpoints.admin.dev import router as dev_router
from app.api.v1.endpoints.admin.feature_flags import router as feature_flags_router
from app.api.v1.endpoints.admin.invoices import router as invoices_router
from app.api.v1.endpoints.admin.organizations import router as organizations_router
from app.api.v1.endpoints.admin.payment_reminders import (
    router as payment_reminders_router,
)
from app.api.v1.endpoints.admin.payments import router as payments_router
from app.api.v1.endpoints.admin.roles import router as roles_router
from app.api.v1.endpoints.admin.system import router as system_router
from app.api.v1.endpoints.admin.users import router as users_router

# Main admin router — all admin sub-routers are included here.
# This is the single router mounted at /admin in the main app router.
router = APIRouter()

# Include existing dev/seed endpoints at the admin root level
router.include_router(dev_router, tags=["Admin - Dev"])

# Dashboard
router.include_router(dashboard_router, prefix="/dashboard", tags=["Admin - Dashboard"])

# Organizations
router.include_router(
    organizations_router, prefix="/organizations", tags=["Admin - Organizations"]
)

# Users
router.include_router(users_router, prefix="/users", tags=["Admin - Users"])

# Invoices
router.include_router(invoices_router, prefix="/invoices", tags=["Admin - Invoices"])

# Payments
router.include_router(payments_router, prefix="/payments", tags=["Admin - Payments"])

# Activity Logs
router.include_router(
    activity_logs_router, prefix="/activity-logs", tags=["Admin - Activity Logs"]
)

# Audit Logs
router.include_router(
    audit_logs_router, prefix="/audit-logs", tags=["Admin - Audit Logs"]
)

# Billing
router.include_router(billing_router, prefix="/billing", tags=["Admin - Billing"])

# Payment Reminders
router.include_router(
    payment_reminders_router,
    prefix="/payment-reminders",
    tags=["Admin - Payment Reminders"],
)

# System Administration
router.include_router(system_router, tags=["Admin - System"])

# Feature Flags
router.include_router(feature_flags_router, prefix="/feature-flags", tags=["Admin - Feature Flags"])

# Roles & Permissions
router.include_router(roles_router, prefix="/roles", tags=["Admin - Roles"])

# Also mount the permissions endpoint at /admin/permissions (not under /roles)
from app.api.v1.endpoints.admin.roles import list_permissions as _list_permissions_fn
_permissions_router = APIRouter()
_permissions_router.add_api_route(
    "",
    _list_permissions_fn,
    methods=["GET"],
    tags=["Admin - Roles"],
    summary="List system admin permissions",
)
router.include_router(_permissions_router, prefix="/permissions")
