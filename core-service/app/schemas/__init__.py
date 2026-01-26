"""Pydantic schemas package"""

from app.schemas.common import PaginationMeta
from app.schemas.item import (
    ItemCreate,
    ItemListItem,
    ItemListResponse,
    ItemResponse,
    ItemUpdate,
)
from app.schemas.item_group import (
    ItemGroupCreate,
    ItemGroupListItem,
    ItemGroupListResponse,
    ItemGroupResponse,
    ItemGroupTreeNode,
    ItemGroupUpdate,
)
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseListItem,
    WarehouseListResponse,
    WarehouseResponse,
    WarehouseTreeNode,
    WarehouseUpdate,
)

__all__ = [
    # Common
    "PaginationMeta",
    # Item
    "ItemCreate",
    "ItemUpdate",
    "ItemResponse",
    "ItemListItem",
    "ItemListResponse",
    # Item Group
    "ItemGroupCreate",
    "ItemGroupUpdate",
    "ItemGroupResponse",
    "ItemGroupListItem",
    "ItemGroupListResponse",
    "ItemGroupTreeNode",
    # Warehouse
    "WarehouseCreate",
    "WarehouseUpdate",
    "WarehouseResponse",
    "WarehouseListItem",
    "WarehouseListResponse",
    "WarehouseTreeNode",
]
