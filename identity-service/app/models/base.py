"""Base model and enum definitions"""

import enum


class UserType(str, enum.Enum):
    """User type enumeration"""

    SYSTEM_ADMIN = "system_admin"
    ORGANIZATION_ADMIN = "organization_admin"
    USER = "user"
    GUEST = "guest"


class UserStatus(str, enum.Enum):
    """User status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class OrganizationType(str, enum.Enum):
    """Organization type enumeration"""

    MASTER = "master"
    CUSTOMER = "customer"
    ENTERPRISE = "enterprise"
    BUSINESS = "business"
    STARTUP = "startup"
    INDIVIDUAL = "individual"


class OrganizationStatus(str, enum.Enum):
    """Organization status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    # New billing statuses for Task 1A-2
    OVERDUE = "overdue"
    DEACTIVATED = "deactivated"


class BillingStatus(str, enum.Enum):
    """Billing status enumeration for organization billing management"""

    ACTIVE = "active"
    TRIAL = "trial"
    OVERDUE = "overdue"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ResourceType(str, enum.Enum):
    """Resource type enumeration"""

    # Identity resources
    USER = "user"
    ORGANIZATION = "organization"
    TEAM = "team"
    ROLE = "role"
    PERMISSION = "permission"
    INVITATION = "invitation"

    # Sales & Orders
    CUSTOMER = "customer"
    SALES_ORDER = "sales_order"
    INVOICE = "invoice"

    # Procurement
    SUPPLIER = "supplier"
    PURCHASE_ORDER = "purchase_order"

    # Inventory resources
    ITEM = "item"
    ITEM_GROUP = "item_group"
    WAREHOUSE = "warehouse"
    STOCK_ENTRY = "stock_entry"
    BATCH = "batch"
    SERIAL = "serial"
    ASN_ORDER = "asn_order"
    PICK_LIST = "pick_list"

    # Accounting
    CHART_OF_ACCOUNT = "chart_of_account"
    PAYMENT = "payment"
    BILLING = "billing"  # Task 1C-1: System admin billing permissions
    
    # Analytics & Reports
    REPORT = "report"
    REPORTING = "reporting"  # Task 1C-1: System admin reporting permissions

    # General
    SETTING = "setting"
    ALL = "all"


class ActionType(str, enum.Enum):
    """Action type enumeration"""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"
    EXECUTE = "execute"
    INVITE = "invite"
