"""System Admin Permission Service for Cross-Organization Access

Task 1C-1 & 1C-2: Implements system admin permissions with cross-organization access
controls and role assignment for master organization users.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.organization import Organization, OrganizationType
from app.models.role import Role, Permission, UserOrganizationRole
from app.services.role_service import RoleService
from app.services.permission_service import PermissionService

logger = logging.getLogger(__name__)


class SystemAdminPermissionService:
    """Service for managing system admin permissions and cross-org access"""

    def __init__(self, db: Session):
        self.db = db
        self.role_service = RoleService(db)
        self.permission_service = PermissionService(db)

    # ── System Admin Role Management ────────────────────────────────────

    def assign_user_as_system_admin(
        self,
        user_id: UUID,
        master_organization_id: UUID,
        admin_type: str = "system_admin_master"
    ) -> UserOrganizationRole:
        """Assign user as system admin with appropriate permissions
        
        Args:
            user_id: User to assign as system admin
            master_organization_id: Master organization ID (validated)
            admin_type: Type of system admin role
        """
        # Validate master organization
        master_org = self._validate_master_organization(master_organization_id)
        
        # Get or create system admin role
        admin_role = self._get_or_create_system_admin_role(admin_type)
        
        # Check if user already has system admin role
        existing_role = (
            self.db.query(UserOrganizationRole)
            .filter(
                UserOrganizationRole.user_id == user_id,
                UserOrganizationRole.organization_id == master_organization_id,
                UserOrganizationRole.role_id == admin_role.id
            )
            .first()
        )
        
        if existing_role:
            logger.info(f"User {user_id} already has system admin role in org {master_organization_id}")
            return existing_role
        
        # Create new system admin role assignment
        user_role = UserOrganizationRole(
            user_id=user_id,
            organization_id=master_organization_id,
            role_id=admin_role.id,
            assigned_by=user_id,  # Self-assigned or system assigned
            is_active=True
        )
        
        self.db.add(user_role)
        self.db.commit()
        self.db.refresh(user_role)
        
        logger.info(f"Assigned user {user_id} as {admin_type} in master org {master_organization_id}")
        return user_role

    def get_system_admin_permissions(self, user_id: UUID) -> List[str]:
        """Get all permissions for system admin user across all organizations
        
        Returns list of permission codes that this system admin has access to
        """
        # Check if user has system admin role in master org
        master_org = self._get_master_organization()
        if not master_org:
            return []
        
        # Query with proper joins to load role data
        user_roles = (
            self.db.query(UserOrganizationRole)
            .join(Role)
            .filter(
                UserOrganizationRole.user_id == user_id,
                UserOrganizationRole.organization_id == master_org.id,
                UserOrganizationRole.is_active == True,
                or_(
                    Role.name.like("system_admin_%"),
                    Role.code == "system_admin"  # Support legacy seed script role
                )
            )
            .all()
        )
        
        if not user_roles:
            return []
        
        # Get all permissions for system admin roles
        permissions = []
        master_admin_found = False
        
        for user_role in user_roles:
            # Get the role by ID to ensure we have the role data
            role = self.db.query(Role).filter(Role.id == user_role.role_id).first()
            if role:
                # Check if this is a master admin role (new or legacy)
                if "system_admin_master" in role.name or role.code == "system_admin":
                    master_admin_found = True
                
                # Get role permissions
                role_permissions = self.role_service.get_role_permissions(user_role.role_id)
                permissions.extend([perm.permission_code for perm in role_permissions])
        
        # If user has system_admin_master role, return wildcard permission
        if master_admin_found:
            permissions.append("*.*")
        
        return list(set(permissions))  # Remove duplicates

    # ── Cross-Organization Access Control ───────────────────────────────

    def can_access_organization(self, user_id: UUID, target_organization_id: UUID) -> bool:
        """Check if system admin user can access target organization
        
        Args:
            user_id: System admin user ID  
            target_organization_id: Organization to access
            
        Returns:
            True if user has cross-org access permission
        """
        permissions = self.get_system_admin_permissions(user_id)
        
        # Check for master permission (all access)
        if "*.*" in permissions:
            return True
        
        # Check for organization-specific permissions
        org_permissions = [
            "system_admin_org_manager",
            "system_admin_user_manager", 
            "system_admin_billing",
            "system_admin_reporting"
        ]
        
        return any(perm in permissions for perm in org_permissions)

    def get_accessible_organizations(self, user_id: UUID) -> List[Organization]:
        """Get list of organizations that system admin can access
        
        Returns all customer organizations if user is system admin
        """
        permissions = self.get_system_admin_permissions(user_id)
        
        if not permissions:
            return []
        
        # If master admin, return all customer organizations  
        if "*.*" in permissions:
            return (
                self.db.query(Organization)
                .filter(Organization.organization_type == OrganizationType.CUSTOMER)
                .all()
            )
        
        # For other admin types, return based on specific permissions
        return (
            self.db.query(Organization)
            .filter(Organization.organization_type == OrganizationType.CUSTOMER)
            .all()
        )

    def assign_customer_organization_to_master(
        self,
        customer_organization_id: UUID,
        master_organization_id: UUID,
        assigned_by: UUID
    ) -> Organization:
        """Link customer organization to master organization
        
        Args:
            customer_organization_id: Customer org to link
            master_organization_id: Master org to link to 
            assigned_by: System admin performing the assignment
        """
        # Validate organizations
        master_org = self._validate_master_organization(master_organization_id)
        
        customer_org = (
            self.db.query(Organization)
            .filter(Organization.id == customer_organization_id)
            .first()
        )
        
        if not customer_org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer organization not found"
            )
        
        if customer_org.organization_type != OrganizationType.CUSTOMER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization must be of type CUSTOMER"
            )
        
        # Update parent organization relationship
        customer_org.parent_organization_id = master_organization_id
        
        self.db.commit()
        self.db.refresh(customer_org)
        
        logger.info(f"Linked customer org {customer_organization_id} to master org {master_organization_id}")
        return customer_org

    # ── Internal Helper Methods ─────────────────────────────────────────

    def _validate_master_organization(self, organization_id: UUID) -> Organization:
        """Validate that organization is a master organization"""
        org = (
            self.db.query(Organization)
            .filter(Organization.id == organization_id)
            .first()
        )
        
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        if org.organization_type != OrganizationType.MASTER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization must be of type MASTER"
            )
        
        return org

    def _get_master_organization(self) -> Optional[Organization]:
        """Get the master organization (should be unique)"""
        return (
            self.db.query(Organization)
            .filter(Organization.organization_type == OrganizationType.MASTER)
            .first()
        )

    def _get_or_create_system_admin_role(self, admin_type: str) -> Role:
        """Get or create system admin role with appropriate permissions"""
        # Check if role exists
        role = (
            self.db.query(Role)
            .filter(Role.name == admin_type)
            .first()
        )
        
        if role:
            return role
        
        # Create new system admin role
        role_data = self._get_system_admin_role_definition(admin_type)
        
        role = Role(
            name=role_data["name"],
            code=role_data["name"],  # Use name as code for system roles
            description=role_data["description"],
            is_system=True,
            is_active=True,
            organization_id=self._get_master_organization().id
        )
        
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        
        logger.info(f"Created new system admin role: {admin_type}")
        return role

    def _get_system_admin_role_definition(self, admin_type: str) -> dict:
        """Get role definition with permissions for different admin types"""
        role_definitions = {
            "system_admin_master": {
                "name": "system_admin_master", 
                "description": "Master system admin with all permissions",
                "permissions": ["*.*"]
            },
            "system_admin_user_manager": {
                "name": "system_admin_user_manager",
                "description": "System admin for user management across organizations", 
                "permissions": [
                    "user.create", "user.read", "user.update", "user.delete",
                    "organization.read", "role.read", "permission.read"
                ]
            },
            "system_admin_org_manager": {
                "name": "system_admin_org_manager",
                "description": "System admin for organization management",
                "permissions": [
                    "organization.create", "organization.read", "organization.update",
                    "organization.delete", "organization.billing_status"
                ]
            },
            "system_admin_billing": {
                "name": "system_admin_billing", 
                "description": "System admin for billing and invoice management",
                "permissions": [
                    "invoice.create", "invoice.read", "invoice.update", "invoice.send_reminder",
                    "payment.create", "payment.read", "organization.billing_status"
                ]
            },
            "system_admin_reporting": {
                "name": "system_admin_reporting",
                "description": "System admin for analytics and cross-org reporting", 
                "permissions": [
                    "analytics.read", "report.generate", "organization.read",
                    "invoice.read", "payment.read", "user.read"
                ]
            }
        }
        
        if admin_type not in role_definitions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown system admin type: {admin_type}"
            )
        
        return role_definitions[admin_type]

    # ── System Admin Users Retrieval ───────────────────────────────────

    def get_system_admin_users(
        self,
        page: int = 1,
        page_size: int = 20,
        permission_type: Optional[str] = None,
        organization_id: Optional[UUID] = None,
        active_only: Optional[bool] = True
    ) -> dict:
        """Get paginated list of system admin users with their permissions and access"""
        from app.models.user import User
        
        # Get master organization
        master_org = self._get_master_organization()
        if not master_org:
            return {"users": [], "total": 0}
        
        # Base query for users with system admin roles
        query = (
            self.db.query(User)
            .join(UserOrganizationRole, User.id == UserOrganizationRole.user_id)
            .join(Role, UserOrganizationRole.role_id == Role.id)
            .filter(
                UserOrganizationRole.organization_id == master_org.id,
                UserOrganizationRole.is_active == True,
                Role.name.like("system_admin_%")
            )
        )
        
        # Apply filters
        if active_only:
            query = query.filter(User.is_active == True)
            
        if permission_type and permission_type != 'all':
            query = query.filter(Role.name.like(f"system_admin_{permission_type}%"))
        
        # Get total count
        total = query.distinct(User.id).count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        users = query.distinct(User.id).offset(offset).limit(page_size).all()
        
        # Enhance users with permissions and organization access
        enhanced_users = []
        for user in users:
            user_permissions = self.get_system_admin_permissions(user.id)
            accessible_orgs = self.get_accessible_organizations(user.id)
            
            # Create enhanced user object
            enhanced_user = user
            enhanced_user.permissions = user_permissions
            enhanced_user.organization_access = [str(org.id) for org in accessible_orgs]
            enhanced_users.append(enhanced_user)
        
        return {
            "users": enhanced_users,
            "total": total
        }

    def get_system_admin_user(self, user_id: UUID):
        """Get specific system admin user with detailed information"""
        from app.models.user import User
        
        # Get master organization
        master_org = self._get_master_organization()
        if not master_org:
            return None
        
        # Check if user has system admin role
        user = (
            self.db.query(User)
            .join(UserOrganizationRole, User.id == UserOrganizationRole.user_id)
            .join(Role, UserOrganizationRole.role_id == Role.id)
            .filter(
                User.id == user_id,
                UserOrganizationRole.organization_id == master_org.id,
                UserOrganizationRole.is_active == True,
                Role.name.like("system_admin_%")
            )
            .first()
        )
        
        if not user:
            return None
        
        # Enhance user with permissions and organization access
        user.permissions = self.get_system_admin_permissions(user.id)
        accessible_orgs = self.get_accessible_organizations(user.id)
        user.organization_access = [str(org.id) for org in accessible_orgs]
        
        return user

    # ── Audit Log Management ────────────────────────────────────────────

    def get_system_admin_audit_logs(
        self,
        admin_user_id: Optional[UUID] = None,
        target_organization_id: Optional[UUID] = None,
        action_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50
    ) -> dict:
        """Get paginated system admin audit logs with filtering
        
        Args:
            admin_user_id: Filter by admin user who performed actions
            target_organization_id: Filter by target organization
            action_type: Filter by action type
            start_date: Filter by start date
            end_date: Filter by end date
            page: Page number for pagination
            page_size: Number of items per page
            
        Returns:
            Dict with audit logs and pagination metadata
        """
        from app.models.audit_log import SystemAdminAuditLog
        from datetime import datetime
        
        # Build base query
        query = self.db.query(SystemAdminAuditLog)
        
        # Apply filters
        if admin_user_id:
            query = query.filter(SystemAdminAuditLog.admin_user_id == admin_user_id)
        
        if target_organization_id:
            query = query.filter(SystemAdminAuditLog.target_organization_id == target_organization_id)
        
        if action_type:
            query = query.filter(SystemAdminAuditLog.action_type == action_type)
        
        if start_date:
            query = query.filter(SystemAdminAuditLog.performed_date >= start_date)
        
        if end_date:
            query = query.filter(SystemAdminAuditLog.performed_date <= end_date)
        
        # Get total count for pagination
        total = query.count()
        
        # Apply pagination and ordering
        offset = (page - 1) * page_size
        audit_logs = (
            query
            .order_by(SystemAdminAuditLog.performed_date.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        
        # Calculate pagination metadata
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "data": audit_logs,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }

    def create_audit_log_entry(
        self,
        action_id: str,
        action_type: str,
        admin_user_id: UUID,
        admin_username: str,
        performed_by: str,
        changes_made: dict,
        target_user_id: Optional[UUID] = None,
        target_username: Optional[str] = None,
        target_organization_id: Optional[UUID] = None,
        target_organization_name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> "SystemAdminAuditLog":
        """Create a new audit log entry for system admin actions
        
        Args:
            action_id: Unique identifier for the action
            action_type: Type of action (assign, update, revoke, etc.)
            admin_user_id: ID of admin user performing action
            admin_username: Username of admin user
            performed_by: Full name of admin user
            changes_made: Dict containing details of changes
            target_user_id: ID of target user (optional)
            target_username: Username of target user (optional)
            target_organization_id: ID of target organization (optional)
            target_organization_name: Name of target organization (optional)
            notes: Optional notes about the action
            
        Returns:
            Created audit log entry
        """
        from app.models.audit_log import SystemAdminAuditLog
        from datetime import datetime
        
        audit_log = SystemAdminAuditLog(
            action_id=action_id,
            action_type=action_type,
            admin_user_id=admin_user_id,
            admin_username=admin_username,
            target_user_id=target_user_id,
            target_username=target_username,
            target_organization_id=target_organization_id,
            target_organization_name=target_organization_name,
            changes_made=changes_made,
            performed_by=performed_by,
            notes=notes,
            performed_date=datetime.utcnow()
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        logger.info(f"Created audit log entry: {action_id} by {admin_username}")
        return audit_log

    def get_audit_log_stats(self) -> dict:
        """Get audit log statistics and metrics
        
        Returns:
            Dict with audit log statistics
        """
        from app.models.audit_log import SystemAdminAuditLog, AuditActionType
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        # Total actions count
        total_actions = self.db.query(SystemAdminAuditLog).count()
        
        # Actions by type
        actions_by_type = {}
        type_counts = (
            self.db.query(
                SystemAdminAuditLog.action_type,
                func.count(SystemAdminAuditLog.id)
            )
            .group_by(SystemAdminAuditLog.action_type)
            .all()
        )
        for action_type, count in type_counts:
            actions_by_type[action_type] = count
        
        # Actions by admin user
        actions_by_admin = {}
        admin_counts = (
            self.db.query(
                SystemAdminAuditLog.admin_username,
                func.count(SystemAdminAuditLog.id)
            )
            .group_by(SystemAdminAuditLog.admin_username)
            .limit(10)  # Top 10 most active admins
            .all()
        )
        for admin_username, count in admin_counts:
            actions_by_admin[admin_username] = count
        
        # Recent actions (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_actions_count = (
            self.db.query(SystemAdminAuditLog)
            .filter(SystemAdminAuditLog.performed_date >= yesterday)
            .count()
        )
        
        # Available action types
        available_action_types = [
            {
                "value": action_type.value,
                "label": action_type.value.replace("_", " ").title(),
                "description": f"{action_type.value.replace('_', ' ').title()} action"
            }
            for action_type in AuditActionType
        ]
        
        return {
            "total_actions": total_actions,
            "actions_by_type": actions_by_type,
            "actions_by_admin": actions_by_admin,
            "recent_actions_count": recent_actions_count,
            "available_action_types": available_action_types
        }