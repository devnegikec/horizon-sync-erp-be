"""
Seed script for system admin roles and permissions.

Creates:
  - 21 system admin permission records (4 domains × 5 perms + 1 master)
  - 5 default system admin roles
  - Role-permission links via RolePermission
  - Assigns Super Admin role to the first system_admin user (if exists and has no system role)

Idempotent: safe to run multiple times — uses check-before-insert.

Usage:
    cd identity-service
    python -m scripts.seed_system_admin_roles
"""

import os
import sys
from datetime import datetime

from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

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
    UserType,
)

# ---------------------------------------------------------------------------
# Permission definitions: 4 domains × 5 actions + 1 master = 21 total
# ---------------------------------------------------------------------------
PERMISSION_DEFS = [
    # Master super-permission
    {
        "code": "system_admin.master",
        "name": "System Admin Master",
        "resource": ResourceType.ALL,
        "action": ActionType.MANAGE,
        "module": "system_admin",
        "description": "Grants access to all system admin endpoints",
    },
    # Users domain
    {
        "code": "system_admin.users_read",
        "name": "System Admin Users Read",
        "resource": ResourceType.USER,
        "action": ActionType.READ,
        "module": "system_admin",
    },
    {
        "code": "system_admin.users_create",
        "name": "System Admin Users Create",
        "resource": ResourceType.USER,
        "action": ActionType.CREATE,
        "module": "system_admin",
    },
    {
        "code": "system_admin.users_update",
        "name": "System Admin Users Update",
        "resource": ResourceType.USER,
        "action": ActionType.UPDATE,
        "module": "system_admin",
    },
    {
        "code": "system_admin.users_delete",
        "name": "System Admin Users Delete",
        "resource": ResourceType.USER,
        "action": ActionType.DELETE,
        "module": "system_admin",
    },
    {
        "code": "system_admin.users_manage",
        "name": "System Admin Users Manage",
        "resource": ResourceType.USER,
        "action": ActionType.MANAGE,
        "module": "system_admin",
    },
    # Organizations domain
    {
        "code": "system_admin.organizations_read",
        "name": "System Admin Organizations Read",
        "resource": ResourceType.ORGANIZATION,
        "action": ActionType.READ,
        "module": "system_admin",
    },
    {
        "code": "system_admin.organizations_create",
        "name": "System Admin Organizations Create",
        "resource": ResourceType.ORGANIZATION,
        "action": ActionType.CREATE,
        "module": "system_admin",
    },
    {
        "code": "system_admin.organizations_update",
        "name": "System Admin Organizations Update",
        "resource": ResourceType.ORGANIZATION,
        "action": ActionType.UPDATE,
        "module": "system_admin",
    },
    {
        "code": "system_admin.organizations_delete",
        "name": "System Admin Organizations Delete",
        "resource": ResourceType.ORGANIZATION,
        "action": ActionType.DELETE,
        "module": "system_admin",
    },
    {
        "code": "system_admin.organizations_manage",
        "name": "System Admin Organizations Manage",
        "resource": ResourceType.ORGANIZATION,
        "action": ActionType.MANAGE,
        "module": "system_admin",
    },
    # Billing domain
    {
        "code": "system_admin.billing_read",
        "name": "System Admin Billing Read",
        "resource": ResourceType.BILLING,
        "action": ActionType.READ,
        "module": "system_admin",
    },
    {
        "code": "system_admin.billing_create",
        "name": "System Admin Billing Create",
        "resource": ResourceType.BILLING,
        "action": ActionType.CREATE,
        "module": "system_admin",
    },
    {
        "code": "system_admin.billing_update",
        "name": "System Admin Billing Update",
        "resource": ResourceType.BILLING,
        "action": ActionType.UPDATE,
        "module": "system_admin",
    },
    {
        "code": "system_admin.billing_delete",
        "name": "System Admin Billing Delete",
        "resource": ResourceType.BILLING,
        "action": ActionType.DELETE,
        "module": "system_admin",
    },
    {
        "code": "system_admin.billing_manage",
        "name": "System Admin Billing Manage",
        "resource": ResourceType.BILLING,
        "action": ActionType.MANAGE,
        "module": "system_admin",
    },
    # Reporting domain
    {
        "code": "system_admin.reporting_read",
        "name": "System Admin Reporting Read",
        "resource": ResourceType.REPORTING,
        "action": ActionType.READ,
        "module": "system_admin",
    },
    {
        "code": "system_admin.reporting_create",
        "name": "System Admin Reporting Create",
        "resource": ResourceType.REPORTING,
        "action": ActionType.CREATE,
        "module": "system_admin",
    },
    {
        "code": "system_admin.reporting_update",
        "name": "System Admin Reporting Update",
        "resource": ResourceType.REPORTING,
        "action": ActionType.UPDATE,
        "module": "system_admin",
    },
    {
        "code": "system_admin.reporting_delete",
        "name": "System Admin Reporting Delete",
        "resource": ResourceType.REPORTING,
        "action": ActionType.DELETE,
        "module": "system_admin",
    },
    {
        "code": "system_admin.reporting_manage",
        "name": "System Admin Reporting Manage",
        "resource": ResourceType.REPORTING,
        "action": ActionType.MANAGE,
        "module": "system_admin",
    },
]

# ---------------------------------------------------------------------------
# Role definitions with their associated permission codes
# ---------------------------------------------------------------------------
ROLE_DEFS = [
    {
        "name": "Super Admin",
        "code": "super_admin",
        "description": "Full system admin access — grants all system_admin permissions",
        "is_system": True,
        "is_default": False,
        "hierarchy_level": 100,
        "permission_codes": ["system_admin.master"],
    },
    {
        "name": "System User Manager",
        "code": "system_user_manager",
        "description": "Manage system admin users (read, create, update, delete)",
        "is_system": True,
        "is_default": False,
        "hierarchy_level": 80,
        "permission_codes": [
            "system_admin.users_read",
            "system_admin.users_create",
            "system_admin.users_update",
            "system_admin.users_delete",
        ],
    },
    {
        "name": "System Org Manager",
        "code": "system_org_manager",
        "description": "Manage organizations (read, create, update, delete)",
        "is_system": True,
        "is_default": False,
        "hierarchy_level": 80,
        "permission_codes": [
            "system_admin.organizations_read",
            "system_admin.organizations_create",
            "system_admin.organizations_update",
            "system_admin.organizations_delete",
        ],
    },
    {
        "name": "System Billing Manager",
        "code": "system_billing_manager",
        "description": "Manage billing (read, create, update, delete)",
        "is_system": True,
        "is_default": False,
        "hierarchy_level": 80,
        "permission_codes": [
            "system_admin.billing_read",
            "system_admin.billing_create",
            "system_admin.billing_update",
            "system_admin.billing_delete",
        ],
    },
    {
        "name": "System Reports Viewer",
        "code": "system_reports_viewer",
        "description": "View system reports and dashboards",
        "is_system": True,
        "is_default": False,
        "hierarchy_level": 50,
        "permission_codes": [
            "system_admin.reporting_read",
        ],
    },
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _get_or_create_master_org(db: Session) -> Organization:
    """Find or create the master organization."""
    master_org = (
        db.query(Organization)
        .filter(Organization.organization_type == OrganizationType.MASTER)
        .first()
    )
    if master_org:
        print(f"  Found existing master org: {master_org.name} ({master_org.id})")
        return master_org

    master_org = Organization(
        name="Master Organization",
        slug="master-org",
        display_name="Master Organization",
        description="Platform-level master organization for system admin roles",
        organization_type=OrganizationType.MASTER,
        status=OrganizationStatus.ACTIVE,
        is_active=True,
    )
    db.add(master_org)
    db.flush()
    print(f"  Created master org: {master_org.name} ({master_org.id})")
    return master_org


def _seed_permissions(db: Session) -> dict:
    """Insert permission records. Returns a dict of code → Permission."""
    perm_map: dict[str, Permission] = {}
    created = 0
    skipped = 0

    for pdef in PERMISSION_DEFS:
        existing = db.query(Permission).filter(Permission.code == pdef["code"]).first()
        if existing:
            perm_map[existing.code] = existing
            skipped += 1
            continue

        perm = Permission(
            code=pdef["code"],
            name=pdef["name"],
            description=pdef.get("description"),
            resource=pdef["resource"],
            action=pdef["action"],
            module=pdef["module"],
        )
        db.add(perm)
        db.flush()
        perm_map[perm.code] = perm
        created += 1

    print(f"  Permissions: {created} created, {skipped} already existed")
    return perm_map


def _seed_roles(db: Session, master_org_id, perm_map: dict) -> dict:
    """Create roles and link permissions. Returns a dict of code → Role."""
    role_map: dict[str, Role] = {}
    roles_created = 0
    roles_skipped = 0
    links_created = 0
    links_skipped = 0

    for rdef in ROLE_DEFS:
        # Find or create the role
        existing_role = (
            db.query(Role)
            .filter(Role.code == rdef["code"], Role.organization_id == master_org_id)
            .first()
        )
        if existing_role:
            role = existing_role
            roles_skipped += 1
        else:
            role = Role(
                organization_id=master_org_id,
                name=rdef["name"],
                code=rdef["code"],
                description=rdef["description"],
                is_system=rdef["is_system"],
                is_default=rdef["is_default"],
                hierarchy_level=rdef["hierarchy_level"],
                is_active=True,
            )
            db.add(role)
            db.flush()
            roles_created += 1

        role_map[role.code] = role

        # Link permissions to role
        for pcode in rdef["permission_codes"]:
            perm = perm_map.get(pcode)
            if not perm:
                print(f"    WARNING: permission '{pcode}' not found — skipping link")
                continue

            existing_link = (
                db.query(RolePermission)
                .filter(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == perm.id,
                )
                .first()
            )
            if existing_link:
                links_skipped += 1
                continue

            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
            links_created += 1

    db.flush()
    print(f"  Roles: {roles_created} created, {roles_skipped} already existed")
    print(f"  RolePermission links: {links_created} created, {links_skipped} already existed")
    return role_map


def _assign_super_admin_to_first_user(
    db: Session, master_org_id, super_admin_role: Role
) -> None:
    """Assign the Super Admin role to the first system_admin user that has no system role."""
    # Find the first system_admin user
    first_admin = (
        db.query(User)
        .filter(User.user_type == UserType.SYSTEM_ADMIN, User.is_active == True)
        .order_by(User.created_at.asc())
        .first()
    )
    if not first_admin:
        print("  No active system_admin user found — skipping role assignment")
        return

    # Check if this user already has a role in the master org
    existing_uor = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == first_admin.id,
            UserOrganizationRole.organization_id == master_org_id,
        )
        .first()
    )
    if existing_uor:
        print(
            f"  User '{first_admin.email}' already has a role in master org — skipping"
        )
        return

    uor = UserOrganizationRole(
        user_id=first_admin.id,
        organization_id=master_org_id,
        role_id=super_admin_role.id,
        is_primary=True,
        is_active=True,
        status="active",
        joined_at=datetime.utcnow(),
    )
    db.add(uor)
    try:
        db.flush()
        print(f"  Assigned Super Admin role to user '{first_admin.email}'")
    except Exception as e:
        db.rollback()
        print(f"  Super Admin role assignment skipped: {e}")


def _seed_org_level_permissions(db: Session) -> None:
    """Seed granular org-level permissions.

    Creates permissions following the `resource.action` pattern (e.g. item.read).
    Module assignment:
      - identity: user, organization, role, permission, invitation
      - core: all business resources (item, invoice, payment, etc.)
    Uses check-before-insert for idempotency.
    """
    # (ResourceType, [ActionType], module)
    ORG_PERMISSION_DEFS: list[tuple[ResourceType, list[ActionType], str]] = [
        # ── Identity service resources ──────────────────────────────
        (ResourceType.USER,         [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "identity"),
        (ResourceType.ORGANIZATION, [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "identity"),
        (ResourceType.ROLE,         [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "identity"),
        (ResourceType.PERMISSION,   [ActionType.READ, ActionType.MANAGE], "identity"),
        (ResourceType.INVITATION,   [ActionType.READ, ActionType.CREATE, ActionType.DELETE, ActionType.MANAGE], "identity"),
        # ── Core service resources ──────────────────────────────────
        (ResourceType.CUSTOMER,       [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.SUPPLIER,       [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.ITEM,           [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.ITEM_GROUP,     [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.WAREHOUSE,      [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.STOCK_ENTRY,    [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.BATCH,          [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.SERIAL,         [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.ASN_ORDER,      [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.PICK_LIST,      [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.INVOICE,        [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.PAYMENT,        [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.SALES_ORDER,    [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.PURCHASE_ORDER, [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.CHART_OF_ACCOUNT, [ActionType.READ, ActionType.CREATE, ActionType.UPDATE, ActionType.DELETE, ActionType.MANAGE], "core"),
        (ResourceType.REPORT,         [ActionType.READ, ActionType.EXECUTE], "core"),
        (ResourceType.SETTING,        [ActionType.READ, ActionType.UPDATE, ActionType.MANAGE], "core"),
    ]

    created = 0
    skipped = 0
    updated = 0

    for resource, actions, module in ORG_PERMISSION_DEFS:
        for action in actions:
            code = f"{resource.value}.{action.value}"
            name = f"{resource.value.replace('_', ' ').title()} {action.value.title()}"

            existing = db.query(Permission).filter(Permission.code == code).first()
            if existing:
                # Update module if it's still set to the old "platform" value
                if existing.module == "platform":
                    existing.module = module
                    updated += 1
                else:
                    skipped += 1
                continue

            perm = Permission(
                code=code,
                name=name,
                resource=resource,
                action=action,
                module=module,
                is_active=True,
            )
            db.add(perm)
            created += 1

    # Ensure *. * wildcard exists with module="identity" (it's an auth concern)
    wildcard_code = "*.*"
    existing_wildcard = db.query(Permission).filter(Permission.code == wildcard_code).first()
    if not existing_wildcard:
        db.add(Permission(
            code=wildcard_code,
            name="Full Access (Wildcard)",
            description="Grants access to all resources and actions",
            resource=ResourceType.ALL,
            action=ActionType.MANAGE,
            module="identity",
            is_active=True,
        ))
        created += 1
    elif existing_wildcard.module == "platform":
        existing_wildcard.module = "identity"
        updated += 1

    db.flush()
    print(f"  Org-level permissions: {created} created, {updated} updated (module fixed), {skipped} already correct")

    # ── Cleanup: deactivate legacy "org.*" shorthand permissions ──────────────
    # The canonical form is "organization.*". Any "org.*" rows are duplicates.
    legacy_org_perms = db.query(Permission).filter(
        Permission.code.like("org.%"),
        Permission.is_active == True,
    ).all()
    cleaned = 0
    for legacy in legacy_org_perms:
        legacy.is_active = False
        cleaned += 1
    if cleaned:
        db.flush()
        print(f"  Cleaned up {cleaned} legacy 'org.*' permissions (deactivated)")


def _seed_org_admin_wildcard(db: Session) -> None:
    """Ensure a *. * wildcard permission exists and every non-master org has an
    organization_admin role linked to it.  Also link existing org_admin users
    who have no role assignment yet."""

    # 1. Ensure the wildcard permission record exists
    wildcard = db.query(Permission).filter(Permission.code == "*.*").first()
    if not wildcard:
        wildcard = Permission(
            code="*.*",
            name="Full Access (Wildcard)",
            description="Grants access to all resources and actions",
            resource=ResourceType.ALL,
            action=ActionType.MANAGE,
            module="identity",
        )
        db.add(wildcard)
        db.flush()
        print("  Created *. * wildcard permission")
    else:
        if wildcard.module == "platform":
            wildcard.module = "identity"
        print("  *. * wildcard permission already exists")

    # 2. For every non-master organization, ensure an organization_admin role exists
    orgs = (
        db.query(Organization)
        .filter(Organization.organization_type != OrganizationType.MASTER)
        .all()
    )
    for org in orgs:
        role = (
            db.query(Role)
            .filter(Role.code == "organization_admin", Role.organization_id == org.id)
            .first()
        )
        if not role:
            role = Role(
                organization_id=org.id,
                name="Organization Admin",
                code="organization_admin",
                description="Full access to all resources within this organization",
                is_system=True,
                is_default=False,
                hierarchy_level=90,
                is_active=True,
            )
            db.add(role)
            db.flush()
            print(f"  Created organization_admin role for org '{org.name}'")

        # Link wildcard permission to the role
        existing_link = (
            db.query(RolePermission)
            .filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == wildcard.id,
            )
            .first()
        )
        if not existing_link:
            db.add(RolePermission(role_id=role.id, permission_id=wildcard.id))
            print(f"  Linked *. * to organization_admin role in org '{org.name}'")

    db.flush()


def _seed_wms_default_roles(db: Session) -> None:
    """Create default WMS roles for every non-master organization.

    Creates 4 roles per org:
      - wms_supervisor  : full warehouse ops across all warehouses
      - wms_manager     : warehouse manager for assigned warehouse(s)
      - wms_operator    : floor worker (scan, pick, put-away)
      - asn_coordinator : manages ASN / inter-warehouse transfers
    """
    orgs = (
        db.query(Organization)
        .filter(Organization.organization_type != OrganizationType.MASTER)
        .all()
    )

    # Permission-code → Permission map for lookup
    perm_codes = [
        "warehouse.read", "warehouse.update",
        "pick_list.read", "pick_list.create", "pick_list.update",
        "pick_list.delete", "pick_list.manage",
        "asn_order.read", "asn_order.create", "asn_order.update",
        "asn_order.delete", "asn_order.manage",
        "stock_entry.read", "stock_entry.create", "stock_entry.update",
        "stock_entry.delete", "stock_entry.manage",
        "item.read", "batch.read", "serial.read",
    ]
    perm_map: dict[str, Permission] = {}
    for code in perm_codes:
        p = db.query(Permission).filter(Permission.code == code).first()
        if p:
            perm_map[code] = p

    WMS_ROLE_DEFS = [
        {
            "name": "WMS Supervisor",
            "code": "wms_supervisor",
            "description": "Full warehouse operations across all warehouses — layout, inbound, put-away, outbound, gate, ASN, and dispatches",
            "hierarchy_level": 75,
            "permission_codes": [
                # warehouse.manage/create/delete removed — global visibility comes from
                # is_primary=True on WarehouseUser, not from a permission shortcut
                "warehouse.read", "warehouse.update",
                "pick_list.read", "pick_list.create", "pick_list.update",
                "pick_list.delete", "pick_list.manage",
                "asn_order.read", "asn_order.create", "asn_order.update",
                "asn_order.delete", "asn_order.manage",
                "stock_entry.read", "stock_entry.create", "stock_entry.update",
                "stock_entry.delete", "stock_entry.manage",
                "item.read", "batch.read", "serial.read",
            ],
        },
        {
            "name": "WMS Manager",
            "code": "wms_manager",
            "description": "Warehouse manager for assigned warehouse(s) — inbound, put-away, outbound, picking, and ASN coordination",
            "hierarchy_level": 70,
            "permission_codes": [
                # warehouse.manage/create/delete removed — managers only see their
                # explicitly assigned warehouses via WarehouseUser rows
                "warehouse.read", "warehouse.update",
                "pick_list.read", "pick_list.create", "pick_list.update",
                "pick_list.delete", "pick_list.manage",
                "asn_order.read", "asn_order.create", "asn_order.update",
                "asn_order.delete", "asn_order.manage",
                "stock_entry.read", "stock_entry.create", "stock_entry.update",
                "stock_entry.delete", "stock_entry.manage",
                "item.read", "batch.read", "serial.read",
            ],
        },
        {
            "name": "WMS Operator",
            "code": "wms_operator",
            "description": "Floor worker — dock scanning, put-away execution, picking, and gate verification",
            "hierarchy_level": 50,
            "permission_codes": [
                "warehouse.read",
                "pick_list.read", "pick_list.update",
                "stock_entry.read",
                "item.read", "batch.read", "serial.read",
            ],
        },
        {
            "name": "ASN Coordinator",
            "code": "asn_coordinator",
            "description": "Manages advance stock notices (ASN) and inter-warehouse transfers — create, confirm, and track fulfillment",
            "hierarchy_level": 65,
            "permission_codes": [
                "asn_order.read", "asn_order.create", "asn_order.update",
                "asn_order.delete", "asn_order.manage",
                "warehouse.read",
                "stock_entry.read",
                "item.read",
                "pick_list.read",
            ],
        },
    ]

    roles_created = 0
    roles_skipped = 0
    links_created = 0
    links_skipped = 0

    for org in orgs:
        for rdef in WMS_ROLE_DEFS:
            role = (
                db.query(Role)
                .filter(Role.code == rdef["code"], Role.organization_id == org.id)
                .first()
            )
            if not role:
                role = Role(
                    organization_id=org.id,
                    name=rdef["name"],
                    code=rdef["code"],
                    description=rdef["description"],
                    is_system=False,
                    is_default=True,
                    hierarchy_level=rdef["hierarchy_level"],
                    is_active=True,
                )
                db.add(role)
                db.flush()
                roles_created += 1
            else:
                roles_skipped += 1

            for pcode in rdef["permission_codes"]:
                perm = perm_map.get(pcode)
                if not perm:
                    continue
                existing_link = (
                    db.query(RolePermission)
                    .filter(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perm.id,
                    )
                    .first()
                )
                if not existing_link:
                    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
                    links_created += 1
                else:
                    links_skipped += 1

    db.flush()
    print(f"  WMS default roles: {roles_created} created, {roles_skipped} already existed")
    print(f"  WMS role-permission links: {links_created} created, {links_skipped} already existed")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def seed_system_admin_roles():
    """Run the full seed process."""
    db: Session = SessionLocal()
    try:
        print("=" * 60)
        print("Seeding system admin roles & permissions")
        print("=" * 60)

        print("\n1. Finding or creating master organization...")
        master_org = _get_or_create_master_org(db)

        print("\n2. Seeding permissions (21 total)...")
        perm_map = _seed_permissions(db)

        print("\n3. Seeding roles and linking permissions...")
        role_map = _seed_roles(db, master_org.id, perm_map)

        # Commit permissions and roles first so they're saved even if assignment fails
        db.commit()

        print("\n4. Assigning Super Admin role to first system_admin user...")
        _assign_super_admin_to_first_user(db, master_org.id, role_map["super_admin"])

        print("\n5.5. Seeding org-level CRUD permissions...")
        _seed_org_level_permissions(db)

        print("\n6. Seeding org-level admin wildcard permission & roles...")
        _seed_org_admin_wildcard(db)

        print("\n7. Seeding WMS default roles for customer organizations...")
        _seed_wms_default_roles(db)

        db.commit()

        print("\n" + "=" * 60)
        print("Seed completed successfully!")
        print("=" * 60)
        print(f"\nMaster org ID : {master_org.id}")
        print(f"Permissions   : {len(perm_map)}")
        print(f"Roles         : {len(role_map)}")
        for code, role in role_map.items():
            print(f"  - {role.name} ({code})")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_system_admin_roles()
