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
from app.schemas.item_price import (
    ItemPriceBulkCreate,
    ItemPriceBulkResponse,
    ItemPriceCreate,
    ItemPriceListItem,
    ItemPriceListResponse,
    ItemPriceResponse,
    ItemPriceUpdate,
)
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseListItem,
    WarehouseListResponse,
    WarehouseResponse,
    WarehouseTreeNode,
    WarehouseUpdate,
)
from app.schemas.rfq import (
    RecordQuoteRequest,
    RFQCreate,
    RFQLineCreate,
    RFQLineResponse,
    RFQListItem,
    RFQListResponse,
    RFQResponse,
    RFQStatusUpdate,
    RFQSupplierCreate,
    RFQSupplierResponse,
    RFQUpdate,
    SupplierQuoteCreate,
    SupplierQuoteResponse,
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
    # Item Price
    "ItemPriceCreate",
    "ItemPriceUpdate",
    "ItemPriceResponse",
    "ItemPriceListItem",
    "ItemPriceListResponse",
    "ItemPriceBulkCreate",
    "ItemPriceBulkResponse",
    # Warehouse
    "WarehouseCreate",
    "WarehouseUpdate",
    "WarehouseResponse",
    "WarehouseListItem",
    "WarehouseListResponse",
    "WarehouseTreeNode",
    # RFQ
    "RFQCreate",
    "RFQUpdate",
    "RFQResponse",
    "RFQListItem",
    "RFQListResponse",
    "RFQStatusUpdate",
    "RFQLineCreate",
    "RFQLineResponse",
    "RFQSupplierCreate",
    "RFQSupplierResponse",
    "SupplierQuoteCreate",
    "SupplierQuoteResponse",
    "RecordQuoteRequest",
]
