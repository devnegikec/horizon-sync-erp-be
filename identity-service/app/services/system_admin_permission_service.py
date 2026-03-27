"""System Admin Permission Service for Cross-Organization Access

Task 1C-1 & 1C-2: Implements system admin permissions with cross-organization access
controls and role assignment for master organization users.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.organization import Organization, OrganizationType
from app.models.permission import Permission
from app.models.role import Role
from app.models.user_organization_role import UserOrganizationRole
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
        
        user_roles = (
            self.db.query(UserOrganizationRole)
            .join(Role)
            .filter(
                UserOrganizationRole.user_id == user_id,
                UserOrganizationRole.organization_id == master_org.id,
                UserOrganizationRole.is_active == True,
                Role.role_name.like("system_admin_%")
            )
            .all()
        )
        
        if not user_roles:
            return []
        
        # Get all permissions for system admin roles
        permissions = []
        for user_role in user_roles:
            role_permissions = self.role_service.get_role_permissions(user_role.role_id)
            permissions.extend([perm.permission_code for perm in role_permissions])
        
        # If user has system_admin_master role, return wildcard permission
        if any("system_admin_master" in ur.role.role_name for ur in user_roles if ur.role):
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
            .filter(Role.role_name == admin_type)
            .first()
        )
        
        if role:
            return role
        
        # Create new system admin role
        role_data = self._get_system_admin_role_definition(admin_type)
        role = self.role_service.create_role(
            role_name=role_data["name"],
            description=role_data["description"],
            permissions=role_data["permissions"]
        )
        
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