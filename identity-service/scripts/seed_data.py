"""Database seeding script"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import (
    User, Organization, Role, Permission, RolePermission,
    UserOrganizationRole, UserType, UserStatus,
    OrganizationType, OrganizationStatus,
    ResourceType, ActionType
)
from app.core.security import hash_password


def seed_database():
    """Seed the database with initial data"""
    db: Session = SessionLocal()
    
    try:
        print("Starting database seeding...")
        
        # Check if data already exists
        existing_org = db.query(Organization).first()
        if existing_org:
            print("Database already seeded. Skipping...")
            return
        
        # 1. Create default organization
        print("Creating default organization...")
        org = Organization(
            name="Default Organization",
            slug="default-org",
            display_name="Default Organization",
            description="Default organization for the system",
            organization_type=OrganizationType.BUSINESS,
            status=OrganizationStatus.ACTIVE,
            is_active=True
        )
        db.add(org)
        db.flush()
        print(f"✓ Created organization: {org.name}")
        
        # 2. Create roles
        print("\nCreating roles...")
        roles_data = [
            {
                "name": "System Administrator",
                "code": "system_admin",
                "description": "Full system access with all permissions",
                "is_system": True,
                "is_default": False,
                "hierarchy_level": 100
            },
            {
                "name": "Organization Administrator",
                "code": "org_admin",
                "description": "Organization-level administrative access",
                "is_system": True,
                "is_default": False,
                "hierarchy_level": 50
            },
            {
                "name": "User",
                "code": "user",
                "description": "Standard user access",
                "is_system": True,
                "is_default": True,
                "hierarchy_level": 10
            }
        ]
        
        roles = {}
        for role_data in roles_data:
            role = Role(
                organization_id=org.id,
                **role_data
            )
            db.add(role)
            db.flush()
            roles[role.code] = role
            print(f"✓ Created role: {role.name}")
        
        # 3. Create permissions
        print("\nCreating permissions...")
        permissions_data = [
            # User permissions
            {"code": "user.create", "name": "Create User", "resource": ResourceType.USER, "action": ActionType.CREATE, "module": "identity"},
            {"code": "user.read", "name": "Read User", "resource": ResourceType.USER, "action": ActionType.READ, "module": "identity"},
            {"code": "user.update", "name": "Update User", "resource": ResourceType.USER, "action": ActionType.UPDATE, "module": "identity"},
            {"code": "user.delete", "name": "Delete User", "resource": ResourceType.USER, "action": ActionType.DELETE, "module": "identity"},
            {"code": "user.manage", "name": "Manage Users", "resource": ResourceType.USER, "action": ActionType.MANAGE, "module": "identity"},
            
            # Organization permissions
            {"code": "org.create", "name": "Create Organization", "resource": ResourceType.ORGANIZATION, "action": ActionType.CREATE, "module": "identity"},
            {"code": "org.read", "name": "Read Organization", "resource": ResourceType.ORGANIZATION, "action": ActionType.READ, "module": "identity"},
            {"code": "org.update", "name": "Update Organization", "resource": ResourceType.ORGANIZATION, "action": ActionType.UPDATE, "module": "identity"},
            {"code": "org.delete", "name": "Delete Organization", "resource": ResourceType.ORGANIZATION, "action": ActionType.DELETE, "module": "identity"},
            {"code": "org.manage", "name": "Manage Organizations", "resource": ResourceType.ORGANIZATION, "action": ActionType.MANAGE, "module": "identity"},
            
            # Role permissions
            {"code": "role.create", "name": "Create Role", "resource": ResourceType.ROLE, "action": ActionType.CREATE, "module": "identity"},
            {"code": "role.read", "name": "Read Role", "resource": ResourceType.ROLE, "action": ActionType.READ, "module": "identity"},
            {"code": "role.update", "name": "Update Role", "resource": ResourceType.ROLE, "action": ActionType.UPDATE, "module": "identity"},
            {"code": "role.delete", "name": "Delete Role", "resource": ResourceType.ROLE, "action": ActionType.DELETE, "module": "identity"},
            {"code": "role.manage", "name": "Manage Roles", "resource": ResourceType.ROLE, "action": ActionType.MANAGE, "module": "identity"},
        ]
        
        permissions = {}
        for perm_data in permissions_data:
            permission = Permission(**perm_data)
            db.add(permission)
            db.flush()
            permissions[perm_data["code"]] = permission
            print(f"✓ Created permission: {permission.name}")
        
        # 4. Assign permissions to roles
        print("\nAssigning permissions to roles...")
        
        # System admin gets all permissions
        for perm in permissions.values():
            role_perm = RolePermission(
                role_id=roles["system_admin"].id,
                permission_id=perm.id
            )
            db.add(role_perm)
        print(f"✓ Assigned all permissions to System Administrator")
        
        # Org admin gets organization and user permissions
        org_admin_perms = [p for code, p in permissions.items() if code.startswith(("org.", "user.read", "user.update"))]
        for perm in org_admin_perms:
            role_perm = RolePermission(
                role_id=roles["org_admin"].id,
                permission_id=perm.id
            )
            db.add(role_perm)
        print(f"✓ Assigned organization permissions to Organization Administrator")
        
        # User gets basic read permissions
        user_perms = [permissions["user.read"], permissions["org.read"]]
        for perm in user_perms:
            role_perm = RolePermission(
                role_id=roles["user"].id,
                permission_id=perm.id
            )
            db.add(role_perm)
        print(f"✓ Assigned basic permissions to User role")
        
        # 5. Create test users
        print("\nCreating test users...")
        users_data = [
            {
                "email": "admin@example.com",
                "password": "Admin123!",
                "first_name": "System",
                "last_name": "Administrator",
                "user_type": UserType.SYSTEM_ADMIN,
                "role_code": "system_admin"
            },
            {
                "email": "john.doe@example.com",
                "password": "User123!",
                "first_name": "John",
                "last_name": "Doe",
                "user_type": UserType.USER,
                "role_code": "user"
            },
            {
                "email": "jane.smith@example.com",
                "password": "User123!",
                "first_name": "Jane",
                "last_name": "Smith",
                "user_type": UserType.USER,
                "role_code": "user"
            }
        ]
        
        for user_data in users_data:
            role_code = user_data.pop("role_code")
            password = user_data.pop("password")
            
            user = User(
                **user_data,
                display_name=f"{user_data['first_name']} {user_data['last_name']}",
                password_hash=hash_password(password),
                status=UserStatus.ACTIVE,
                email_verified=True,
                email_verified_at=datetime.utcnow(),
                is_active=True
            )
            db.add(user)
            db.flush()
            
            # Assign role to user
            user_org_role = UserOrganizationRole(
                user_id=user.id,
                organization_id=org.id,
                role_id=roles[role_code].id,
                is_primary=True,
                is_active=True,
                status="active",
                joined_at=datetime.utcnow()
            )
            db.add(user_org_role)
            
            print(f"✓ Created user: {user.email} (Role: {role_code})")
        
        # Commit all changes
        db.commit()
        
        print("\n" + "="*50)
        print("Database seeding completed successfully!")
        print("="*50)
        print("\nTest Credentials:")
        print("-" * 50)
        print("System Admin:")
        print("  Email: admin@example.com")
        print("  Password: Admin123!")
        print("\nRegular Users:")
        print("  Email: john.doe@example.com")
        print("  Password: User123!")
        print("\n  Email: jane.smith@example.com")
        print("  Password: User123!")
        print("-" * 50)
        
    except Exception as e:
        print(f"\n✗ Error during seeding: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
