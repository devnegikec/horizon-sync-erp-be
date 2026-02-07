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

    # Accounting
    CHART_OF_ACCOUNT = "chart_of_account"
    PAYMENT = "payment"

    # General
    REPORT = "report"
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
