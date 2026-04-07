"""System Administration API Endpoints

Endpoints for managing system-wide settings, master organization, admin users,
system statistics, and health monitoring.
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.services.admin_organization_service import AdminOrganizationService
from app.services.admin_user_service import AdminUserService

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request/Response Models ─────────────────────────────────────────

class SubscriptionConfig(BaseModel):
    """Subscription configuration settings"""
    default_seat_limit: int = Field(default=10, ge=1)
    default_credit_limit: int = Field(default=10000, ge=0)
    base_price_per_seat: float = Field(default=25.0, ge=0)
    credit_rate: float = Field(default=0.02, ge=0)
    billing_cycles: List[str] = Field(default=["monthly", "quarterly", "yearly"])


class SystemConfig(BaseModel):
    """System configuration settings"""
    auto_deactivate_enabled: bool = Field(default=True)
    auto_deactivate_days: int = Field(default=30, ge=1)
    grace_period_days: int = Field(default=7, ge=0)
    reminder_frequency_days: int = Field(default=7, ge=1)


class SystemSettings(BaseModel):
    """Complete system settings response"""
    master_organization: Dict
    subscription_config: SubscriptionConfig
    system_config: SystemConfig


class SystemSettingsUpdate(BaseModel):
    """System settings update request"""
    subscription_config: Optional[SubscriptionConfig] = None
    system_config: Optional[SystemConfig] = None


class SystemAdminUser(BaseModel):
    """System admin user response"""
    user_id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    roles: List[str]
    is_active: bool
    created_at: str
    last_login: Optional[str]


class AdminUserCreate(BaseModel):
    """Admin user creation request"""
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    password: Optional[str] = Field(None, min_length=8)
    roles: List[str] = Field(default=["system_admin_master"])
    send_invitation: bool = Field(default=True)


class SystemStats(BaseModel):
    """System statistics response"""
    total_organizations: int
    active_organizations: int
    overdue_organizations: int
    total_users: int
    active_users: int
    total_invoices: int
    overdue_invoices: int
    total_revenue: str


class ServiceHealth(BaseModel):
    """Individual service health status"""
    database: str = Field(..., pattern=r'^(ok|error)$')
    identity_service: str = Field(..., pattern=r'^(ok|error)$')
    core_service: str = Field(..., pattern=r'^(ok|error)$')
    search_service: str = Field(..., pattern=r'^(ok|error)$')


class SystemHealth(BaseModel):
    """System health overview"""
    status: str = Field(..., pattern=r'^(healthy|warning|error)$')
    services: ServiceHealth
    timestamp: str


# ── API Endpoints ──────────────────────────────────────────────────

@router.get(
    "/system/settings",
    response_model=SystemSettings,
    summary="Get system settings",
    description="Get comprehensive system settings including master org and configurations"
)
async def get_system_settings(
    current_user = Depends(require_permission("system_admin.master")),
    db: Session = Depends(get_db),
):
    """Get system-wide settings and configurations"""
    try:
        # Get master organization details
        admin_org_service = AdminOrganizationService(db)
        master_org = await admin_org_service.get_master_organization()
        
        # Default configurations (would come from database in real implementation)
        subscription_config = SubscriptionConfig()
        system_config = SystemConfig()
        
        return SystemSettings(
            master_organization=master_org or {},
            subscription_config=subscription_config,
            system_config=system_config
        )
        
    except Exception as e:
        logger.error(f"Error retrieving system settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system settings"
        )


@router.patch(
    "/system/settings",
    response_model=SystemSettings,
    summary="Update system settings",
    description="Update system-wide configurations"
)
async def update_system_settings(
    updates: SystemSettingsUpdate,
    current_user = Depends(require_permission("system_admin.master")),
    db: Session = Depends(get_db),
):
    """Update system settings"""
    try:
        # In a real implementation, these would be saved to a system_config table
        logger.info(f"System settings update requested: {updates}")
        
        # Return updated settings
        return await get_system_settings(current_user, db)
        
    except Exception as e:
        logger.error(f"Error updating system settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update system settings"
        )


@router.get(
    "/system/master-organization",
    summary="Get master organization details",
    description="Get detailed information about the master organization"
)
async def get_master_organization(
    request: Request,
    current_user = Depends(require_permission("system_admin.master")),
    db: Session = Depends(get_db),
):
    """Get master organization details"""
    try:
        # Extract token from Authorization header
        token = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            
        admin_org_service = AdminOrganizationService(db, token=token)
        master_org = await admin_org_service.get_master_organization()
        
        if not master_org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Master organization not found"
            )
        
        return master_org
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving master organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve master organization"
        )


@router.patch(
    "/system/master-organization",
    summary="Update master organization",
    description="Update master organization details"
)
async def update_master_organization(
    updates: Dict,
    request: Request,
    current_user = Depends(require_permission("system_admin.master")),
    db: Session = Depends(get_db),
):
    """Update master organization details"""
    try:
        # Extract token from Authorization header
        token = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            
        admin_org_service = AdminOrganizationService(db, token=token)
        updated_org = await admin_org_service.update_master_organization(updates)
        
        return updated_org
        
    except Exception as e:
        logger.error(f"Error updating master organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update master organization"
        )


@router.get(
    "/system/admin-users",
    summary="Get system admin users",
    description="Get all users with system admin roles"
)
async def get_system_admin_users(
    current_user = Depends(require_permission("system_admin.master")),
    db: Session = Depends(get_db),
):
    """Get system admin users in master organization"""
    try:
        admin_user_service = AdminUserService(db)
        users = await admin_user_service.get_system_admin_users()
        
        return {
            "users": users,
            "total": len(users)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving system admin users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system admin users"
        )


@router.post(
    "/system/admin-users",
    response_model=SystemAdminUser,
    summary="Create system admin user",
    description="Create a new system admin user"
)
async def create_system_admin_user(
    user_data: AdminUserCreate,
    current_user = Depends(require_permission("system_admin.master")),
    db: Session = Depends(get_db),
):
    """Create new system admin user"""
    try:
        admin_user_service = AdminUserService(db)
        new_user = await admin_user_service.create_system_admin_user(user_data.dict())
        
        return new_user
        
    except Exception as e:
        logger.error(f"Error creating system admin user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create system admin user"
        )


@router.patch(
    "/system/admin-users/{user_id}",
    response_model=SystemAdminUser,
    summary="Update system admin user",
    description="Update system admin user details"
)
async def update_system_admin_user(
    user_id: UUID,
    updates: Dict,
    current_user = Depends(require_permission("system_admin.master")),
    db: Session = Depends(get_db),
):
    """Update system admin user"""
    try:
        admin_user_service = AdminUserService(db)
        updated_user = await admin_user_service.update_system_admin_user(user_id, updates)
        
        return updated_user
        
    except Exception as e:
        logger.error(f"Error updating system admin user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update system admin user"
        )


@router.delete(
    "/system/admin-users/{user_id}",
    summary="Remove system admin user",
    description="Deactivate system admin user"
)
async def remove_system_admin_user(
    user_id: UUID,
    current_user = Depends(require_permission("system_admin.master")),
    db: Session = Depends(get_db),
):
    """Remove (deactivate) system admin user"""
    try:
        admin_user_service = AdminUserService(db)
        await admin_user_service.remove_system_admin_user(user_id)
        
        return {"message": "System admin user removed successfully"}
        
    except Exception as e:
        logger.error(f"Error removing system admin user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove system admin user"
        )


@router.get(
    "/system/stats",
    response_model=SystemStats,
    summary="Get system statistics",
    description="Get comprehensive system statistics and metrics"
)
async def get_system_stats(
    current_user = Depends(require_permission("system_admin.master")),
    db: Session = Depends(get_db),
):
    """Get system-wide statistics"""
    try:
        # This would query actual database tables for real stats
        # For now, returning mock data structure
        stats = SystemStats(
            total_organizations=0,
            active_organizations=0,
            overdue_organizations=0,
            total_users=0,
            active_users=0,
            total_invoices=0,
            overdue_invoices=0,
            total_revenue="0.00"
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system statistics"
        )


@router.get(
    "/system/health",
    response_model=SystemHealth,
    summary="Check system health",
    description="Get system health status including all services"
)
async def get_system_health(
    current_user = Depends(require_permission("system_admin.master")),
    db: Session = Depends(get_db),
):
    """Check system health across all services"""
    try:
        import datetime
        
        # Basic health check - in real implementation would test actual services
        services = ServiceHealth(
            database="ok",  # Would test DB connection
            identity_service="ok",  # Would ping identity service
            core_service="ok",  # This service is running
            search_service="ok"  # Would ping search service
        )
        
        # Determine overall status
        service_statuses = [services.database, services.identity_service, 
                          services.core_service, services.search_service]
        
        if all(status == "ok" for status in service_statuses):
            overall_status = "healthy"
        elif any(status == "error" for status in service_statuses):
            overall_status = "error"
        else:
            overall_status = "warning"
        
        health = SystemHealth(
            status=overall_status,
            services=services,
            timestamp=datetime.datetime.utcnow().isoformat()
        )
        
        return health
        
    except Exception as e:
        logger.error(f"Error checking system health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check system health"
        )