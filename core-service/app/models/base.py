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


class BatchStatus(str, enum.Enum):
    """Batch status enumeration"""

    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    RECALLED = "RECALLED"


class StockEntryType(str, enum.Enum):
    """Stock entry type enumeration"""

    MATERIAL_RECEIPT = "MATERIAL_RECEIPT"
    MATERIAL_ISSUE = "MATERIAL_ISSUE"
    MATERIAL_TRANSFER = "MATERIAL_TRANSFER"
    MANUFACTURE = "MANUFACTURE"
    REPACK = "REPACK"
    SEND_TO_SUBCONTRACTOR = "SEND_TO_SUBCONTRACTOR"


class StockEntryStatus(str, enum.Enum):
    """Stock entry status enumeration"""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    CANCELLED = "CANCELLED"


class MovementType(str, enum.Enum):
    """Movement type enumeration"""

    PURCHASE = "PURCHASE"
    SALE = "SALE"
    TRANSFER = "TRANSFER"
    ADJUSTMENT = "ADJUSTMENT"
    RETURN = "RETURN"
    DAMAGE = "DAMAGE"


class InspectionType(str, enum.Enum):
    """Quality inspection type enumeration"""

    INCOMING = "INCOMING"
    OUTGOING = "OUTGOING"
    IN_PROCESS = "IN_PROCESS"


class InspectionStatus(str, enum.Enum):
    """Quality inspection status enumeration"""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class ReadingType(str, enum.Enum):
    """Quality inspection reading type enumeration"""

    NUMERIC = "NUMERIC"
    TEXT = "TEXT"
    PASS_FAIL = "PASS_FAIL"
