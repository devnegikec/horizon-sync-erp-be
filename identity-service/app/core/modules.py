"""
Module registry — maps ERP modules to their permission codes and metadata.

This is the single source of truth for:
  - Which modules exist in the platform
  - Which permission codes belong to each module
  - Display metadata (label, icon, description) for the role creation UI

The registry is used by:
  1. The seed script to create preloaded roles with correct permission sets
  2. The permissions API to return module-grouped responses
  3. The frontend role creation UI to render module-level toggles
"""

from dataclasses import dataclass, field


@dataclass
class ModuleResource:
    """A resource within a module (e.g. 'Items' inside 'Inventory')."""

    key: str  # matches Permission.resource value, e.g. "item"
    label: str  # human-readable, e.g. "Items"
    actions: list[str] = field(
        default_factory=lambda: ["read", "create", "update", "delete"]
    )


@dataclass
class ModuleDefinition:
    """A top-level ERP module grouping related resources."""

    key: str  # matches Permission.module value, e.g. "inventory"
    label: str  # human-readable, e.g. "Inventory"
    description: str
    icon: str  # icon name for the frontend
    resources: list[ModuleResource] = field(default_factory=list)

    @property
    def all_permission_codes(self) -> list[str]:
        """Return every permission code that belongs to this module."""
        codes = []
        for resource in self.resources:
            for action in resource.actions:
                codes.append(f"{resource.key}.{action}")
        return codes

    @property
    def read_permission_codes(self) -> list[str]:
        """Return only read-level permission codes for this module."""
        return [f"{r.key}.read" for r in self.resources if "read" in r.actions]


# ─────────────────────────────────────────────────────────────────────────────
# Module Definitions
# ─────────────────────────────────────────────────────────────────────────────

MODULES: list[ModuleDefinition] = [
    ModuleDefinition(
        key="identity",
        label="Identity & Access",
        description="Manage users, roles, permissions, and organization settings",
        icon="shield",
        resources=[
            ModuleResource(
                "user",
                "Users",
                ["read", "create", "update", "delete", "manage", "invite"],
            ),
            ModuleResource(
                "role", "Roles", ["read", "create", "update", "delete", "manage"]
            ),
            ModuleResource("org", "Organization", ["read", "update"]),
            ModuleResource("invitation", "Invitations", ["create"]),
        ],
    ),
    ModuleDefinition(
        key="sales",
        label="Sales & Orders",
        description="Manage customers, sales orders, quotations, and invoices",
        icon="shopping-cart",
        resources=[
            ModuleResource("customer", "Customers"),
            ModuleResource("sales_order", "Sales Orders"),
            ModuleResource("invoice", "Invoices", ["read", "create", "update"]),
        ],
    ),
    ModuleDefinition(
        key="procurement",
        label="Procurement",
        description="Manage suppliers, purchase orders, and RFQs",
        icon="truck",
        resources=[
            ModuleResource("supplier", "Suppliers"),
            ModuleResource("purchase_order", "Purchase Orders"),
        ],
    ),
    ModuleDefinition(
        key="inventory",
        label="Inventory",
        description="Manage items, warehouses, stock entries, batches, serials, pick lists, and ASN orders",
        icon="box",
        resources=[
            ModuleResource("item", "Items"),
            ModuleResource(
                "warehouse",
                "Warehouses",
                ["read", "create", "update", "delete", "manage"],
            ),
            ModuleResource(
                "stock_entry",
                "Stock Movements",
                ["read", "create", "update", "delete", "manage"],
            ),
            ModuleResource("batch", "Batches", ["read"]),
            ModuleResource("serial", "Serial Numbers", ["read"]),
            ModuleResource(
                "pick_list",
                "Pick Lists",
                ["read", "create", "update", "delete", "manage"],
            ),
            ModuleResource(
                "asn_order",
                "ASN Orders",
                ["read", "create", "update", "delete", "manage"],
            ),
        ],
    ),
    ModuleDefinition(
        key="accounting",
        label="Accounting",
        description="Manage chart of accounts, payments, and financial records",
        icon="calculator",
        resources=[
            ModuleResource(
                "chart_of_account", "Chart of Accounts", ["read", "create", "update"]
            ),
            ModuleResource("payment", "Payments", ["read", "create", "update"]),
        ],
    ),
]

# Lookup helpers
MODULE_BY_KEY: dict[str, ModuleDefinition] = {m.key: m for m in MODULES}


def get_module(key: str) -> ModuleDefinition | None:
    """Return a module definition by its key."""
    return MODULE_BY_KEY.get(key)


def get_all_permission_codes() -> list[str]:
    """Return every permission code across all modules."""
    codes = []
    for module in MODULES:
        codes.extend(module.all_permission_codes)
    return codes


def get_module_for_permission_code(code: str) -> ModuleDefinition | None:
    """Given a permission code like 'item.read', return its parent module."""
    if "." not in code:
        return None
    resource_key = code.split(".")[0]
    for module in MODULES:
        for resource in module.resources:
            if resource.key == resource_key:
                return module
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Preloaded Role Templates
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class RoleTemplate:
    """A preloaded role template seeded for every new organization."""

    code: str
    name: str
    description: str
    is_system: bool
    hierarchy_level: int
    permission_codes: list[str]


def _codes(*modules_and_extras: str | list[str]) -> list[str]:
    """Helper to build a permission code list from module keys and/or explicit codes."""
    result = []
    for item in modules_and_extras:
        if isinstance(item, list):
            result.extend(item)
        elif item in MODULE_BY_KEY:
            result.extend(MODULE_BY_KEY[item].all_permission_codes)
        else:
            result.append(item)
    return result


PRELOADED_ORG_ROLES: list[RoleTemplate] = [
    RoleTemplate(
        code="owner",
        name="Organization Owner",
        description="Full access to all features. Automatically assigned to the user who created the organization.",
        is_system=True,
        hierarchy_level=100,
        permission_codes=["*.*"],
    ),
    RoleTemplate(
        code="org_admin",
        name="Administrator",
        description="Full access to identity management plus read-only access to all business modules.",
        is_system=True,
        hierarchy_level=80,
        permission_codes=_codes(
            "identity",
            MODULE_BY_KEY["sales"].read_permission_codes,
            MODULE_BY_KEY["procurement"].read_permission_codes,
            MODULE_BY_KEY["inventory"].read_permission_codes,
            MODULE_BY_KEY["accounting"].read_permission_codes,
        ),
    ),
    RoleTemplate(
        code="sales_agent",
        name="Sales Agent",
        description="Full access to Sales & Orders module plus read-only Inventory.",
        is_system=True,
        hierarchy_level=40,
        permission_codes=_codes(
            "sales",
            MODULE_BY_KEY["inventory"].read_permission_codes,
        ),
    ),
    RoleTemplate(
        code="procurement_officer",
        name="Procurement Officer",
        description="Full access to Procurement module plus read-only Inventory.",
        is_system=True,
        hierarchy_level=40,
        permission_codes=_codes(
            "procurement",
            MODULE_BY_KEY["inventory"].read_permission_codes,
        ),
    ),
    RoleTemplate(
        code="accountant",
        name="Accountant",
        description="Full access to Accounting module plus read-only access to Sales invoices.",
        is_system=True,
        hierarchy_level=40,
        permission_codes=_codes(
            "accounting",
            ["invoice.read"],
        ),
    ),
    RoleTemplate(
        code="warehouse_staff",
        name="Warehouse Staff",
        description="Full access to Inventory module only.",
        is_system=True,
        hierarchy_level=20,
        permission_codes=_codes("inventory"),
    ),
    RoleTemplate(
        code="viewer",
        name="Viewer",
        description="Read-only access across all modules. Cannot create, edit, or delete anything.",
        is_system=True,
        hierarchy_level=10,
        permission_codes=_codes(
            MODULE_BY_KEY["sales"].read_permission_codes,
            MODULE_BY_KEY["procurement"].read_permission_codes,
            MODULE_BY_KEY["inventory"].read_permission_codes,
            MODULE_BY_KEY["accounting"].read_permission_codes,
        ),
    ),
    # ── WMS Roles ────────────────────────────────────────────────────────────
    RoleTemplate(
        code="wms_admin",
        name="WMS Admin",
        description="Full warehouse administration — global access to all warehouses, layout, inbound, put-away, outbound, gate, ASN, dispatches, and worker/device management",
        is_system=False,
        hierarchy_level=75,
        permission_codes=[
            # WMS Admin gets warehouse.manage for global visibility and admin operations
            "warehouse.read",
            "warehouse.create",
            "warehouse.update",
            "warehouse.delete",
            "warehouse.manage",
            "pick_list.read",
            "pick_list.create",
            "pick_list.update",
            "pick_list.delete",
            "pick_list.manage",
            "asn_order.read",
            "asn_order.create",
            "asn_order.update",
            "asn_order.delete",
            "asn_order.manage",
            "stock_entry.read",
            "stock_entry.create",
            "stock_entry.update",
            "stock_entry.delete",
            "stock_entry.manage",
            "item.read",
            "batch.read",
            "serial.read",
        ],
    ),
    RoleTemplate(
        code="wms_manager",
        name="WMS Manager",
        description="Warehouse manager for assigned warehouse(s) — inbound, put-away, outbound, picking, and ASN coordination",
        is_system=False,
        hierarchy_level=70,
        permission_codes=[
            # Managers can read and update their assigned warehouses only.
            # warehouse.manage/create/delete are admin-level permissions that would bypass
            # the WarehouseUser scoping and expose all org warehouses.
            "warehouse.read",
            "warehouse.update",
            "pick_list.read",
            "pick_list.create",
            "pick_list.update",
            "pick_list.delete",
            "pick_list.manage",
            "asn_order.read",
            "asn_order.create",
            "asn_order.update",
            "asn_order.delete",
            "asn_order.manage",
            "stock_entry.read",
            "stock_entry.create",
            "stock_entry.update",
            "stock_entry.delete",
            "stock_entry.manage",
            "item.read",
            "batch.read",
            "serial.read",
        ],
    ),
    RoleTemplate(
        code="wms_operator",
        name="WMS Operator",
        description="Floor worker — dock scanning, put-away execution, picking, and gate verification",
        is_system=False,
        hierarchy_level=50,
        permission_codes=[
            "warehouse.read",
            "pick_list.read",
            "pick_list.update",
            "stock_entry.read",
            "item.read",
            "batch.read",
            "serial.read",
        ],
    ),
    RoleTemplate(
        code="asn_coordinator",
        name="ASN Coordinator",
        description="Manages advance stock notices (ASN) and inter-warehouse transfers — create, confirm, and track fulfillment",
        is_system=False,
        hierarchy_level=65,
        permission_codes=[
            "asn_order.read",
            "asn_order.create",
            "asn_order.update",
            "asn_order.delete",
            "asn_order.manage",
            "warehouse.read",
            "stock_entry.read",
            "item.read",
            "pick_list.read",
        ],
    ),
    # ── QR Code Login Worker ─────────────────────────────────────────────────
    RoleTemplate(
        code="warehouse_work_user",
        name="Warehouse Work User",
        description="Limited warehouse worker — QR login only. Can scan, create/read/update receiving slips, and read/update pick lists.",
        is_system=True,
        hierarchy_level=5,
        permission_codes=[
            "warehouse.read",
            "wms.scan",
            "receiving_slip.create",
            "receiving_slip.read",
            "receiving_slip.update",
            "pick_list.read",
            "pick_list.update",
        ],
    ),
]

PRELOADED_ROLE_BY_CODE: dict[str, RoleTemplate] = {
    r.code: r for r in PRELOADED_ORG_ROLES
}
