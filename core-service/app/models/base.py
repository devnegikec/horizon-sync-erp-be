"""Base model and enum definitions for inventory management"""

import enum


class ItemType(str, enum.Enum):
    """Item type enumeration"""

    STOCK = "STOCK"
    NON_STOCK = "NON_STOCK"
    SERVICE = "SERVICE"
    FIXED_ASSET = "FIXED_ASSET"


class ItemStatus(str, enum.Enum):
    """Item status enumeration"""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DISCONTINUED = "DISCONTINUED"


class ValuationMethod(str, enum.Enum):
    """Inventory valuation method enumeration"""

    FIFO = "FIFO"
    LIFO = "LIFO"
    MOVING_AVERAGE = "MOVING_AVERAGE"
    STANDARD = "STANDARD"


class DocumentStatus(str, enum.Enum):
    """Document status enumeration"""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    CANCELLED = "CANCELLED"


class WarehouseType(str, enum.Enum):
    """Warehouse type enumeration"""

    WAREHOUSE = "WAREHOUSE"
    STORE = "STORE"
    VIRTUAL = "VIRTUAL"
    TRANSIT = "TRANSIT"
