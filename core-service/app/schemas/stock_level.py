"""Stock level schemas"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from app.models.stock_level import StockLevel

from app.schemas.common import PaginationMeta


class ProductInfo(BaseModel):
    """Product (item) name and code from Items table."""

    name: str
    code: str


class WarehouseInfo(BaseModel):
    """Warehouse name and code from warehouses_extended table."""

    name: str
    code: str


class StockLevelBase(BaseModel):
    item_id: UUID  # API uses item_id; model has product_id
    warehouse_id: UUID
    quantity_on_hand: int = 0
    quantity_reserved: int = 0
    quantity_available: int | None = None  # if not set, computed as on_hand - reserved
    last_counted_at: datetime | None = None


class StockLevelCreate(StockLevelBase):
    pass


class StockLevelUpdate(BaseModel):
    quantity_on_hand: int | None = None
    quantity_reserved: int | None = None
    quantity_available: int | None = None
    last_counted_at: datetime | None = None


class StockLevelResponse(BaseModel):
    id: UUID
    organization_id: UUID
    product_id: UUID  # item id
    warehouse_id: UUID
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    last_counted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    product: ProductInfo | None = None
    warehouse: WarehouseInfo | None = None

    model_config = ConfigDict(from_attributes=True)


class StockLevelListItem(BaseModel):
    id: UUID
    product_id: UUID
    warehouse_id: UUID
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    last_counted_at: datetime | None = None
    updated_at: datetime
    product: ProductInfo | None = None
    warehouse: WarehouseInfo | None = None

    model_config = ConfigDict(from_attributes=True)


class StockLevelListResponse(BaseModel):
    stock_levels: list[StockLevelListItem]
    pagination: PaginationMeta


def stock_level_to_list_item(s: "StockLevel") -> StockLevelListItem:
    """Build list item from ORM without embedding Item/Warehouse (avoids lazy-load loops)."""
    product = None
    if getattr(s, "product", None) is not None:
        product = ProductInfo(name=s.product.item_name, code=s.product.item_code)
    warehouse = None
    if getattr(s, "warehouse", None) is not None:
        warehouse = WarehouseInfo(name=s.warehouse.name, code=s.warehouse.code)
    return StockLevelListItem(
        id=s.id,
        product_id=s.product_id,
        warehouse_id=s.warehouse_id,
        quantity_on_hand=s.quantity_on_hand or 0,
        quantity_reserved=s.quantity_reserved or 0,
        quantity_available=s.quantity_available or 0,
        last_counted_at=s.last_counted_at,
        updated_at=s.updated_at,
        product=product,
        warehouse=warehouse,
    )


def stock_level_to_response(s: "StockLevel") -> StockLevelResponse:
    """Build response from ORM without embedding Item/Warehouse (avoids lazy-load loops)."""
    product = None
    if getattr(s, "product", None) is not None:
        product = ProductInfo(name=s.product.item_name, code=s.product.item_code)
    warehouse = None
    if getattr(s, "warehouse", None) is not None:
        warehouse = WarehouseInfo(name=s.warehouse.name, code=s.warehouse.code)
    return StockLevelResponse(
        id=s.id,
        organization_id=s.organization_id,
        product_id=s.product_id,
        warehouse_id=s.warehouse_id,
        quantity_on_hand=s.quantity_on_hand or 0,
        quantity_reserved=s.quantity_reserved or 0,
        quantity_available=s.quantity_available or 0,
        last_counted_at=s.last_counted_at,
        created_at=s.created_at,
        updated_at=s.updated_at,
        product=product,
        warehouse=warehouse,
    )
