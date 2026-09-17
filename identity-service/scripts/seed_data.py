"""Database seeding script"""

import os
import sys
from datetime import datetime

from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.security import hash_password  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    ActionType,
    Organization,
    OrganizationStatus,
    OrganizationType,
    Permission,
    ResourceType,
    Role,
    RolePermission,
    User,
    UserOrganizationRole,
    UserStatus,
    UserType,
)


def _seed_missing_permissions(db: Session) -> None:
    """Idempotently seed any permissions that are missing from the database.

    Called when the org already exists but permissions may have been
    missed on a previous partial run.
    """
    # Same full list as in seed_database()
    permissions_data = [
        {
            "code": "user.create",
            "name": "Create User",
            "resource": ResourceType.USER,
            "action": ActionType.CREATE,
            "module": "identity",
        },
        {
            "code": "user.read",
            "name": "Read User",
            "resource": ResourceType.USER,
            "action": ActionType.READ,
            "module": "identity",
        },
        {
            "code": "user.update",
            "name": "Update User",
            "resource": ResourceType.USER,
            "action": ActionType.UPDATE,
            "module": "identity",
        },
        {
            "code": "user.delete",
            "name": "Delete User",
            "resource": ResourceType.USER,
            "action": ActionType.DELETE,
            "module": "identity",
        },
        {
            "code": "user.manage",
            "name": "Manage Users",
            "resource": ResourceType.USER,
            "action": ActionType.MANAGE,
            "module": "identity",
        },
        {
            "code": "user.invite",
            "name": "Invite User",
            "resource": ResourceType.USER,
            "action": ActionType.INVITE,
            "module": "identity",
        },
        {
            "code": "invitation.create",
            "name": "Create Invitation",
            "resource": ResourceType.INVITATION,
            "action": ActionType.CREATE,
            "module": "identity",
        },
        {
            "code": "org.create",
            "name": "Create Organization",
            "resource": ResourceType.ORGANIZATION,
            "action": ActionType.CREATE,
            "module": "identity",
        },
        {
            "code": "org.read",
            "name": "Read Organization",
            "resource": ResourceType.ORGANIZATION,
            "action": ActionType.READ,
            "module": "identity",
        },
        {
            "code": "org.update",
            "name": "Update Organization",
            "resource": ResourceType.ORGANIZATION,
            "action": ActionType.UPDATE,
            "module": "identity",
        },
        {
            "code": "org.delete",
            "name": "Delete Organization",
            "resource": ResourceType.ORGANIZATION,
            "action": ActionType.DELETE,
            "module": "identity",
        },
        {
            "code": "org.manage",
            "name": "Manage Organizations",
            "resource": ResourceType.ORGANIZATION,
            "action": ActionType.MANAGE,
            "module": "identity",
        },
        {
            "code": "role.create",
            "name": "Create Role",
            "resource": ResourceType.ROLE,
            "action": ActionType.CREATE,
            "module": "identity",
        },
        {
            "code": "role.read",
            "name": "Read Role",
            "resource": ResourceType.ROLE,
            "action": ActionType.READ,
            "module": "identity",
        },
        {
            "code": "role.update",
            "name": "Update Role",
            "resource": ResourceType.ROLE,
            "action": ActionType.UPDATE,
            "module": "identity",
        },
        {
            "code": "role.delete",
            "name": "Delete Role",
            "resource": ResourceType.ROLE,
            "action": ActionType.DELETE,
            "module": "identity",
        },
        {
            "code": "role.manage",
            "name": "Manage Roles",
            "resource": ResourceType.ROLE,
            "action": ActionType.MANAGE,
            "module": "identity",
        },
        {
            "code": "*.*",
            "name": "Full access (all resources and actions)",
            "resource": ResourceType.ALL,
            "action": ActionType.MANAGE,
            "module": "identity",
        },
        {
            "code": "system.admin",
            "name": "System Administrator access",
            "resource": ResourceType.ALL,
            "action": ActionType.MANAGE,
            "module": "identity",
        },
        {
            "code": "user.*",
            "name": "All user actions",
            "resource": ResourceType.USER,
            "action": ActionType.MANAGE,
            "module": "identity",
        },
        {
            "code": "org.*",
            "name": "All organization actions",
            "resource": ResourceType.ORGANIZATION,
            "action": ActionType.MANAGE,
            "module": "identity",
        },
        {
            "code": "role.*",
            "name": "All role actions",
            "resource": ResourceType.ROLE,
            "action": ActionType.MANAGE,
            "module": "identity",
        },
        {
            "code": "warehouse.read",
            "name": "Read Warehouse",
            "resource": ResourceType.WAREHOUSE,
            "action": ActionType.READ,
            "module": "inventory",
        },
        {
            "code": "warehouse.create",
            "name": "Create Warehouse",
            "resource": ResourceType.WAREHOUSE,
            "action": ActionType.CREATE,
            "module": "inventory",
        },
        {
            "code": "warehouse.update",
            "name": "Update Warehouse",
            "resource": ResourceType.WAREHOUSE,
            "action": ActionType.UPDATE,
            "module": "inventory",
        },
        {
            "code": "warehouse.delete",
            "name": "Delete Warehouse",
            "resource": ResourceType.WAREHOUSE,
            "action": ActionType.DELETE,
            "module": "inventory",
        },
        {
            "code": "warehouse.manage",
            "name": "Manage Warehouses",
            "resource": ResourceType.WAREHOUSE,
            "action": ActionType.MANAGE,
            "module": "inventory",
        },
        {
            "code": "stock_entry.read",
            "name": "Read Stock Movement",
            "resource": ResourceType.STOCK_ENTRY,
            "action": ActionType.READ,
            "module": "inventory",
        },
        {
            "code": "stock_entry.create",
            "name": "Create Stock Movement",
            "resource": ResourceType.STOCK_ENTRY,
            "action": ActionType.CREATE,
            "module": "inventory",
        },
        {
            "code": "stock_entry.update",
            "name": "Update Stock Movement",
            "resource": ResourceType.STOCK_ENTRY,
            "action": ActionType.UPDATE,
            "module": "inventory",
        },
        {
            "code": "stock_entry.delete",
            "name": "Delete Stock Movement",
            "resource": ResourceType.STOCK_ENTRY,
            "action": ActionType.DELETE,
            "module": "inventory",
        },
        {
            "code": "stock_entry.manage",
            "name": "Manage Stock Movements",
            "resource": ResourceType.STOCK_ENTRY,
            "action": ActionType.MANAGE,
            "module": "inventory",
        },
        {
            "code": "pick_list.read",
            "name": "Read Pick List",
            "resource": ResourceType.PICK_LIST,
            "action": ActionType.READ,
            "module": "inventory",
        },
        {
            "code": "pick_list.create",
            "name": "Create Pick List",
            "resource": ResourceType.PICK_LIST,
            "action": ActionType.CREATE,
            "module": "inventory",
        },
        {
            "code": "pick_list.update",
            "name": "Update Pick List",
            "resource": ResourceType.PICK_LIST,
            "action": ActionType.UPDATE,
            "module": "inventory",
        },
        {
            "code": "pick_list.delete",
            "name": "Delete Pick List",
            "resource": ResourceType.PICK_LIST,
            "action": ActionType.DELETE,
            "module": "inventory",
        },
        {
            "code": "pick_list.manage",
            "name": "Manage Pick Lists",
            "resource": ResourceType.PICK_LIST,
            "action": ActionType.MANAGE,
            "module": "inventory",
        },
        {
            "code": "asn_order.read",
            "name": "Read ASN Order",
            "resource": ResourceType.ASN_ORDER,
            "action": ActionType.READ,
            "module": "inventory",
        },
        {
            "code": "asn_order.create",
            "name": "Create ASN Order",
            "resource": ResourceType.ASN_ORDER,
            "action": ActionType.CREATE,
            "module": "inventory",
        },
        {
            "code": "asn_order.update",
            "name": "Update ASN Order",
            "resource": ResourceType.ASN_ORDER,
            "action": ActionType.UPDATE,
            "module": "inventory",
        },
        {
            "code": "asn_order.delete",
            "name": "Delete ASN Order",
            "resource": ResourceType.ASN_ORDER,
            "action": ActionType.DELETE,
            "module": "inventory",
        },
        {
            "code": "asn_order.manage",
            "name": "Manage ASN Orders",
            "resource": ResourceType.ASN_ORDER,
            "action": ActionType.MANAGE,
            "module": "inventory",
        },
        {
            "code": "item.read",
            "name": "Read Item",
            "resource": ResourceType.ITEM,
            "action": ActionType.READ,
            "module": "inventory",
        },
        {
            "code": "batch.read",
            "name": "Read Batch",
            "resource": ResourceType.BATCH,
            "action": ActionType.READ,
            "module": "inventory",
        },
        {
            "code": "serial.read",
            "name": "Read Serial Number",
            "resource": ResourceType.SERIAL,
            "action": ActionType.READ,
            "module": "inventory",
        },
        {
            "code": "wms.scan",
            "name": "WMS Scan",
            "resource": ResourceType.WAREHOUSE,
            "action": ActionType.SCAN,
            "module": "inventory",
        },
        {
            "code": "receiving_slip.create",
            "name": "Create Receiving Slip",
            "resource": ResourceType.RECEIVING_SLIP,
            "action": ActionType.CREATE,
            "module": "inventory",
        },
        {
            "code": "receiving_slip.read",
            "name": "Read Receiving Slip",
            "resource": ResourceType.RECEIVING_SLIP,
            "action": ActionType.READ,
            "module": "inventory",
        },
        {
            "code": "receiving_slip.update",
            "name": "Update Receiving Slip",
            "resource": ResourceType.RECEIVING_SLIP,
            "action": ActionType.UPDATE,
            "module": "inventory",
        },
    ]

    # Get existing permission codes
    existing_codes = set(row[0] for row in db.query(Permission.code).all())

    created = 0
    for perm_data in permissions_data:
        if perm_data["code"] in existing_codes:
            continue
        db.add(Permission(**perm_data))
        created += 1

    if created:
        db.commit()
        print(f"✓ Created {created} missing permissions")
    else:
        print("✓ All permissions already exist — nothing to seed")


def seed_database():
    """Seed the database with initial data"""
    db: Session = SessionLocal()

    try:
        print("Starting database seeding...")

        # Check if data already exists (org check) but still seed missing permissions
        existing_org = db.query(Organization).first()
        if existing_org:
            print("Organization already exists. Seeding only missing permissions...")
            _seed_missing_permissions(db)
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
            is_active=True,
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
                "hierarchy_level": 100,
            },
            {
                "name": "Organization Administrator",
                "code": "org_admin",
                "description": "Organization-level administrative access",
                "is_system": True,
                "is_default": False,
                "hierarchy_level": 50,
            },
            {
                "name": "User",
                "code": "user",
                "description": "Standard user access",
                "is_system": True,
                "is_default": True,
                "hierarchy_level": 10,
            },
            {
                "name": "Warehouse Work User",
                "code": "warehouse_work_user",
                "description": "Limited warehouse worker access — QR login only, scan/read/update receiving slips and pick lists",
                "is_system": True,
                "is_default": False,
                "hierarchy_level": 5,
            },
        ]

        roles = {}
        for role_data in roles_data:
            role = Role(organization_id=org.id, **role_data)
            db.add(role)
            db.flush()
            roles[role.code] = role
            print(f"✓ Created role: {role.name}")

        # 3. Create permissions
        print("\nCreating permissions...")
        permissions_data = [
            # User permissions
            {
                "code": "user.create",
                "name": "Create User",
                "resource": ResourceType.USER,
                "action": ActionType.CREATE,
                "module": "identity",
            },
            {
                "code": "user.read",
                "name": "Read User",
                "resource": ResourceType.USER,
                "action": ActionType.READ,
                "module": "identity",
            },
            {
                "code": "user.update",
                "name": "Update User",
                "resource": ResourceType.USER,
                "action": ActionType.UPDATE,
                "module": "identity",
            },
            {
                "code": "user.delete",
                "name": "Delete User",
                "resource": ResourceType.USER,
                "action": ActionType.DELETE,
                "module": "identity",
            },
            {
                "code": "user.manage",
                "name": "Manage Users",
                "resource": ResourceType.USER,
                "action": ActionType.MANAGE,
                "module": "identity",
            },
            {
                "code": "user.invite",
                "name": "Invite User",
                "resource": ResourceType.USER,
                "action": ActionType.INVITE,
                "module": "identity",
            },
            {
                "code": "invitation.create",
                "name": "Create Invitation",
                "resource": ResourceType.INVITATION,
                "action": ActionType.CREATE,
                "module": "identity",
            },
            # Organization permissions
            {
                "code": "org.create",
                "name": "Create Organization",
                "resource": ResourceType.ORGANIZATION,
                "action": ActionType.CREATE,
                "module": "identity",
            },
            {
                "code": "org.read",
                "name": "Read Organization",
                "resource": ResourceType.ORGANIZATION,
                "action": ActionType.READ,
                "module": "identity",
            },
            {
                "code": "org.update",
                "name": "Update Organization",
                "resource": ResourceType.ORGANIZATION,
                "action": ActionType.UPDATE,
                "module": "identity",
            },
            {
                "code": "org.delete",
                "name": "Delete Organization",
                "resource": ResourceType.ORGANIZATION,
                "action": ActionType.DELETE,
                "module": "identity",
            },
            {
                "code": "org.manage",
                "name": "Manage Organizations",
                "resource": ResourceType.ORGANIZATION,
                "action": ActionType.MANAGE,
                "module": "identity",
            },
            # Role permissions
            {
                "code": "role.create",
                "name": "Create Role",
                "resource": ResourceType.ROLE,
                "action": ActionType.CREATE,
                "module": "identity",
            },
            {
                "code": "role.read",
                "name": "Read Role",
                "resource": ResourceType.ROLE,
                "action": ActionType.READ,
                "module": "identity",
            },
            {
                "code": "role.update",
                "name": "Update Role",
                "resource": ResourceType.ROLE,
                "action": ActionType.UPDATE,
                "module": "identity",
            },
            {
                "code": "role.delete",
                "name": "Delete Role",
                "resource": ResourceType.ROLE,
                "action": ActionType.DELETE,
                "module": "identity",
            },
            {
                "code": "role.manage",
                "name": "Manage Roles",
                "resource": ResourceType.ROLE,
                "action": ActionType.MANAGE,
                "module": "identity",
            },
            # Wildcard permissions (grant all actions for a resource or everything)
            {
                "code": "*.*",
                "name": "Full access (all resources and actions)",
                "resource": ResourceType.ALL,
                "action": ActionType.MANAGE,
                "module": "identity",
            },
            {
                "code": "system.admin",
                "name": "System Administrator access",
                "resource": ResourceType.ALL,
                "action": ActionType.MANAGE,
                "module": "identity",
            },
            {
                "code": "user.*",
                "name": "All user actions",
                "resource": ResourceType.USER,
                "action": ActionType.MANAGE,
                "module": "identity",
            },
            {
                "code": "org.*",
                "name": "All organization actions",
                "resource": ResourceType.ORGANIZATION,
                "action": ActionType.MANAGE,
                "module": "identity",
            },
            {
                "code": "role.*",
                "name": "All role actions",
                "resource": ResourceType.ROLE,
                "action": ActionType.MANAGE,
                "module": "identity",
            },
            # WMS / Warehouse permissions
            {
                "code": "warehouse.read",
                "name": "Read Warehouse",
                "resource": ResourceType.WAREHOUSE,
                "action": ActionType.READ,
                "module": "inventory",
            },
            {
                "code": "warehouse.create",
                "name": "Create Warehouse",
                "resource": ResourceType.WAREHOUSE,
                "action": ActionType.CREATE,
                "module": "inventory",
            },
            {
                "code": "warehouse.update",
                "name": "Update Warehouse",
                "resource": ResourceType.WAREHOUSE,
                "action": ActionType.UPDATE,
                "module": "inventory",
            },
            {
                "code": "warehouse.delete",
                "name": "Delete Warehouse",
                "resource": ResourceType.WAREHOUSE,
                "action": ActionType.DELETE,
                "module": "inventory",
            },
            {
                "code": "warehouse.manage",
                "name": "Manage Warehouses",
                "resource": ResourceType.WAREHOUSE,
                "action": ActionType.MANAGE,
                "module": "inventory",
            },
            {
                "code": "stock_entry.read",
                "name": "Read Stock Movement",
                "resource": ResourceType.STOCK_ENTRY,
                "action": ActionType.READ,
                "module": "inventory",
            },
            {
                "code": "stock_entry.create",
                "name": "Create Stock Movement",
                "resource": ResourceType.STOCK_ENTRY,
                "action": ActionType.CREATE,
                "module": "inventory",
            },
            {
                "code": "stock_entry.update",
                "name": "Update Stock Movement",
                "resource": ResourceType.STOCK_ENTRY,
                "action": ActionType.UPDATE,
                "module": "inventory",
            },
            {
                "code": "stock_entry.delete",
                "name": "Delete Stock Movement",
                "resource": ResourceType.STOCK_ENTRY,
                "action": ActionType.DELETE,
                "module": "inventory",
            },
            {
                "code": "stock_entry.manage",
                "name": "Manage Stock Movements",
                "resource": ResourceType.STOCK_ENTRY,
                "action": ActionType.MANAGE,
                "module": "inventory",
            },
            {
                "code": "pick_list.read",
                "name": "Read Pick List",
                "resource": ResourceType.PICK_LIST,
                "action": ActionType.READ,
                "module": "inventory",
            },
            {
                "code": "pick_list.create",
                "name": "Create Pick List",
                "resource": ResourceType.PICK_LIST,
                "action": ActionType.CREATE,
                "module": "inventory",
            },
            {
                "code": "pick_list.update",
                "name": "Update Pick List",
                "resource": ResourceType.PICK_LIST,
                "action": ActionType.UPDATE,
                "module": "inventory",
            },
            {
                "code": "pick_list.delete",
                "name": "Delete Pick List",
                "resource": ResourceType.PICK_LIST,
                "action": ActionType.DELETE,
                "module": "inventory",
            },
            {
                "code": "pick_list.manage",
                "name": "Manage Pick Lists",
                "resource": ResourceType.PICK_LIST,
                "action": ActionType.MANAGE,
                "module": "inventory",
            },
            {
                "code": "asn_order.read",
                "name": "Read ASN Order",
                "resource": ResourceType.ASN_ORDER,
                "action": ActionType.READ,
                "module": "inventory",
            },
            {
                "code": "asn_order.create",
                "name": "Create ASN Order",
                "resource": ResourceType.ASN_ORDER,
                "action": ActionType.CREATE,
                "module": "inventory",
            },
            {
                "code": "asn_order.update",
                "name": "Update ASN Order",
                "resource": ResourceType.ASN_ORDER,
                "action": ActionType.UPDATE,
                "module": "inventory",
            },
            {
                "code": "asn_order.delete",
                "name": "Delete ASN Order",
                "resource": ResourceType.ASN_ORDER,
                "action": ActionType.DELETE,
                "module": "inventory",
            },
            {
                "code": "asn_order.manage",
                "name": "Manage ASN Orders",
                "resource": ResourceType.ASN_ORDER,
                "action": ActionType.MANAGE,
                "module": "inventory",
            },
            {
                "code": "item.read",
                "name": "Read Item",
                "resource": ResourceType.ITEM,
                "action": ActionType.READ,
                "module": "inventory",
            },
            {
                "code": "batch.read",
                "name": "Read Batch",
                "resource": ResourceType.BATCH,
                "action": ActionType.READ,
                "module": "inventory",
            },
            {
                "code": "serial.read",
                "name": "Read Serial Number",
                "resource": ResourceType.SERIAL,
                "action": ActionType.READ,
                "module": "inventory",
            },
            # WMS warehouse worker permissions (QR login)
            {
                "code": "wms.scan",
                "name": "WMS Scan",
                "resource": ResourceType.WAREHOUSE,
                "action": ActionType.SCAN,
                "module": "inventory",
            },
            {
                "code": "receiving_slip.create",
                "name": "Create Receiving Slip",
                "resource": ResourceType.RECEIVING_SLIP,
                "action": ActionType.CREATE,
                "module": "inventory",
            },
            {
                "code": "receiving_slip.read",
                "name": "Read Receiving Slip",
                "resource": ResourceType.RECEIVING_SLIP,
                "action": ActionType.READ,
                "module": "inventory",
            },
            {
                "code": "receiving_slip.update",
                "name": "Update Receiving Slip",
                "resource": ResourceType.RECEIVING_SLIP,
                "action": ActionType.UPDATE,
                "module": "inventory",
            },
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
                role_id=roles["system_admin"].id, permission_id=perm.id
            )
            db.add(role_perm)
        print("✓ Assigned all permissions to System Administrator")

        # Org admin gets organization and user permissions
        org_admin_perms = [
            p
            for code, p in permissions.items()
            if code.startswith(
                ("org.", "user.read", "user.update", "user.invite", "invitation.create")
            )
        ]
        for perm in org_admin_perms:
            role_perm = RolePermission(
                role_id=roles["org_admin"].id, permission_id=perm.id
            )
            db.add(role_perm)
        print("✓ Assigned organization permissions to Organization Administrator")

        # User gets basic read permissions
        user_perms = [permissions["user.read"], permissions["org.read"]]
        for perm in user_perms:
            role_perm = RolePermission(role_id=roles["user"].id, permission_id=perm.id)
            db.add(role_perm)
        print("✓ Assigned basic permissions to User role")

        # Warehouse work user gets WMS scan + receiving slip + pick list permissions
        try:
            warehouse_worker_perms = [
                permissions["warehouse.read"],
                permissions["wms.scan"],
                permissions["receiving_slip.create"],
                permissions["receiving_slip.read"],
                permissions["receiving_slip.update"],
                permissions["pick_list.read"],
                permissions["pick_list.update"],
                permissions["stock_entry.create"],
                permissions["stock_entry.read"],
            ]
            for perm in warehouse_worker_perms:
                role_perm = RolePermission(
                    role_id=roles["warehouse_work_user"].id, permission_id=perm.id
                )
                db.add(role_perm)
            print("✓ Assigned WMS permissions to Warehouse Work User role")
        except KeyError as e:
            print(f"⚠ Warning: Could not assign permission {e} — skipping")

        # 5. Create test users
        print("\nCreating test users...")
        users_data = [
            {
                "email": "admin@example.com",
                "password": "Admin123!",
                "first_name": "System",
                "last_name": "Administrator",
                "user_type": UserType.SYSTEM_ADMIN,
                "role_code": "system_admin",
            },
            {
                "email": "john.doe@example.com",
                "password": "User123!",
                "first_name": "John",
                "last_name": "Doe",
                "user_type": UserType.USER,
                "role_code": "user",
            },
            {
                "email": "jane.smith@example.com",
                "password": "User123!",
                "first_name": "Jane",
                "last_name": "Smith",
                "user_type": UserType.USER,
                "role_code": "user",
            },
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
                is_active=True,
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
                joined_at=datetime.utcnow(),
            )
            db.add(user_org_role)

            print(f"✓ Created user: {user.email} (Role: {role_code})")

        # Commit all changes
        db.commit()

        print("\n" + "=" * 50)
        print("Database seeding completed successfully!")
        print("=" * 50)
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
