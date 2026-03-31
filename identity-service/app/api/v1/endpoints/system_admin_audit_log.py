"""System Admin Audit Log API endpoints

Provides endpoints for retrieving system admin audit logs with filtering
and pagination for compliance and monitoring purposes.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.audit_log import (
    AuditLogFilters,
    AuditLogStatsResponse,
    SystemAdminAuditLogListResponse,
)
from app.services.system_admin_permission_service import SystemAdminPermissionService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_system_admin_permission_service(db: Session = Depends(get_db)):
    """Dependency to get system admin permission service"""
    return SystemAdminPermissionService(db)


def verify_system_admin_access(
    current_user: User = Depends(get_current_user),
    service: SystemAdminPermissionService = Depends(get_system_admin_permission_service)
):
    """Verify current user has system admin access"""
    permissions = service.get_system_admin_permissions(current_user.id)
    
    if not permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System admin access required"
        )
    
    return current_user


@router.get(
    "/system-admin-audit-log",
    response_model=SystemAdminAuditLogListResponse,
    summary="Get system admin audit logs",
    description="Retrieve paginated system admin audit logs with filtering options"
)
async def get_system_admin_audit_logs(
    admin_user_id: Optional[UUID] = Query(None, description="Filter by admin user ID"),
    target_organization_id: Optional[UUID] = Query(None, description="Filter by target organization ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO format)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    current_user: User = Depends(verify_system_admin_access),
    service: SystemAdminPermissionService = Depends(get_system_admin_permission_service)
):
    """
    Get paginated system admin audit logs with filtering.
    
    **Required Permissions**: System admin access
    
    **Filtering Options**:
    - `admin_user_id`: Filter by admin user who performed actions
    - `target_organization_id`: Filter by target organization
    - `action_type`: Filter by action type (assign, update, revoke, access_grant, access_revoke)
    - `start_date`: Filter by start date (ISO format: 2023-01-01T00:00:00Z)
    - `end_date`: Filter by end date (ISO format: 2023-01-31T23:59:59Z)
    
    **Pagination**:
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (1-500, default: 50)
    
    **Response Structure**:
    ```json
    {
        "data": [
            {
                "action_id": "string",
                "action_type": "assign",
                "admin_user_id": "uuid",
                "admin_username": "string",
                "target_user_id": "uuid",
                "target_username": "string", 
                "target_organization_id": "uuid",
                "target_organization_name": "string",
                "changes_made": {},
                "performed_by": "string",
                "notes": "string",
                "performed_date": "2023-01-01T12:00:00Z",
                "created_at": "2023-01-01T12:00:00Z"
            }
        ],
        "pagination": {
            "page": 1,
            "page_size": 50,
            "total_items": 100,
            "total_pages": 2,
            "has_next": true,
            "has_prev": false
        }
    }
    ```
    """
    try:
        result = service.get_system_admin_audit_logs(
            admin_user_id=admin_user_id,
            target_organization_id=target_organization_id,
            action_type=action_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size
        )
        
        logger.info(
            f"Retrieved {len(result['data'])} audit logs (page {page}) "
            f"for user {current_user.email}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to retrieve audit logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs"
        )


@router.get(
    "/system-admin-audit-log/stats",
    response_model=AuditLogStatsResponse,
    summary="Get audit log statistics",
    description="Retrieve statistics and metrics about system admin audit logs"
)
async def get_audit_log_stats(
    current_user: User = Depends(verify_system_admin_access),
    service: SystemAdminPermissionService = Depends(get_system_admin_permission_service)
):
    """
    Get audit log statistics and metrics.
    
    **Required Permissions**: System admin access
    
    **Response Structure**:
    ```json
    {
        "total_actions": 150,
        "actions_by_type": {
            "assign": 50,
            "update": 30,
            "revoke": 20,
            "access_grant": 25,
            "access_revoke": 25
        },
        "actions_by_admin": {
            "admin1@example.com": 50,
            "admin2@example.com": 30
        },
        "recent_actions_count": 5,
        "available_action_types": [
            {
                "value": "assign",
                "label": "Assign",
                "description": "Assign action"
            }
        ]
    }
    ```
    """
    try:
        stats = service.get_audit_log_stats()
        
        logger.info(f"Retrieved audit log stats for user {current_user.email}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to retrieve audit log stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit log statistics"
        )