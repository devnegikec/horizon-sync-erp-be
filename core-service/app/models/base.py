"""Base model and enum definitions for inventory management"""

import enum


class ItemType(str, enum.Enum):
    """Item type enumeration"""

    STOCK = "stock"
    NON_STOCK = "non_stock"
    SERVICE = "service"
    FIXED_ASSET = "fixed_asset"


class ItemStatus(str, enum.Enum):
    """Item status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"


class ValuationMethod(str, enum.Enum):
    """Inventory valuation method enumeration"""

    FIFO = "fifo"
    LIFO = "lifo"
    MOVING_AVERAGE = "moving_average"
    STANDARD = "standard"


class DocumentStatus(str, enum.Enum):
    """Document status enumeration"""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"


class WarehouseType(str, enum.Enum):
    """Warehouse type enumeration"""

    WAREHOUSE = "warehouse"
    STORE = "store"
    VIRTUAL = "virtual"
    TRANSIT = "transit"
