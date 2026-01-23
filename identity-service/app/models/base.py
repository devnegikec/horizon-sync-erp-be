"""Base model and enum definitions"""

import enum
from app.database import Base


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
    USER = "user"
    ORGANIZATION = "organization"
    TEAM = "team"
    ROLE = "role"
    PERMISSION = "permission"


class ActionType(str, enum.Enum):
    """Action type enumeration"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"
    EXECUTE = "execute"
