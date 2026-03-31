"""System Admin Users Management API Endpoints 

API endpoints for managing system admin users and their permissions across organizations.
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.services.system_admin_permission_service import SystemAdminPermissionService
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Response Models ─────────────────────────────────────────────────

class SystemAdminUserResponse(BaseModel):
    """Response model for system admin user"""
    user_id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    permissions: List[str]
    organization_access: List[str]
    created_at: str
    last_login: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class SystemAdminUsersListResponse(BaseModel):
    """Response model for paginated system admin users list"""
    admin_users: List[SystemAdminUserResponse]
    total: int
    page: int
    page_size: int


# ── API Endpoints ─────────────────────────────────────────────────

@router.get(
    "/system-admin-users",
    response_model=SystemAdminUsersListResponse,
    summary="List system admin users",
    description="Get paginated list of system admin users with their permissions and organization access"
)
async def get_system_admin_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    permission_type: Optional[str] = Query(None, description="Filter by permission type"),
    organization_id: Optional[UUID] = Query(None, description="Filter by organization access"),
    active_only: Optional[bool] = Query(True, description="Show only active admin users"),
    current_user = Depends(require_permission("system_admin.master")),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of system admin users.
    
    Requires system_admin.master permission.
    """
    
    service = SystemAdminPermissionService(db)
    
    try:
        result = service.get_system_admin_users(
            page=page,
            page_size=page_size,
            permission_type=permission_type,
            organization_id=organization_id,
            active_only=active_only
        )
        
        return SystemAdminUsersListResponse(
            admin_users=[
                SystemAdminUserResponse(
                    user_id=user.id,
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    permissions=user.permissions or [],
                    organization_access=user.organization_access or [],
                    created_at=user.created_at.isoformat() if user.created_at else "",
                    last_login=user.last_login.isoformat() if user.last_login else None,
                    is_active=user.is_active
                )
                for user in result["users"]
            ],
            total=result["total"],
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error retrieving system admin users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system admin users"
        )


@router.get(
    "/system-admin-users/{user_id}",
    response_model=SystemAdminUserResponse,
    summary="Get system admin user details",
    description="Get detailed information about a specific system admin user"
)
async def get_system_admin_user(
    user_id: UUID,
    current_user = Depends(require_permission("system_admin.master")),
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific system admin user.
    
    Requires system_admin.master permission.
    """
    
    service = SystemAdminPermissionService(db)
    
    try:
        user = service.get_system_admin_user(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System admin user not found"
            )
            
        return SystemAdminUserResponse(
            user_id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            permissions=user.permissions or [],
            organization_access=user.organization_access or [],
            created_at=user.created_at.isoformat() if user.created_at else "",
            last_login=user.last_login.isoformat() if user.last_login else None,
            is_active=user.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving system admin user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system admin user"
        )