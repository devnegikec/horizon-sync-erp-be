"""Stock movement schemas"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.stock_movement import StockMovement

from app.schemas.common import PaginationMeta


class ProductInfo(BaseModel):
    """Product (item) name and code from Items table."""

    name: str
    code: str


class WarehouseInfo(BaseModel):
    """Warehouse name and code from warehouses_extended table."""

    name: str
    code: str


class StockMovementCreate(BaseModel):
    item_id: UUID  # product_id in DB
    warehouse_id: UUID
    movement_type: str  # in, out, transfer, adjustment
    quantity: int = Field(..., gt=0)
    unit_cost: Decimal | float | None = None
    reference_type: str | None = Field(None, max_length=50)
    reference_id: UUID | None = None
    notes: str | None = None
    performed_at: datetime | None = None


class StockMovementResponse(BaseModel):
    id: UUID
    organization_id: UUID
    product_id: UUID
    warehouse_id: UUID
    movement_type: str
    quantity: int
    unit_cost: Decimal | None = None
    reference_type: str | None = None
    reference_id: UUID | None = None
    notes: str | None = None
    performed_by: UUID | None = None
    performed_at: datetime
    created_at: datetime
    updated_at: datetime
    product: ProductInfo | None = None
    warehouse: WarehouseInfo | None = None

    model_config = ConfigDict(from_attributes=True)


class StockMovementListItem(BaseModel):
    id: UUID
    product_id: UUID
    warehouse_id: UUID
    movement_type: str
    quantity: int
    performed_at: datetime
    created_at: datetime
    product: ProductInfo | None = None
    warehouse: WarehouseInfo | None = None

    model_config = ConfigDict(from_attributes=True)


class StockMovementListResponse(BaseModel):
    stock_movements: list[StockMovementListItem]
    pagination: PaginationMeta


def stock_movement_to_list_item(m: StockMovement) -> StockMovementListItem:
    """Build list item from ORM without embedding Item/Warehouse (avoids lazy-load loops)."""

    product = None
    if getattr(m, "product", None) is not None:
        product = ProductInfo(name=m.product.item_name, code=m.product.item_code)
    warehouse = None
    if getattr(m, "warehouse", None) is not None:
        warehouse = WarehouseInfo(name=m.warehouse.name, code=m.warehouse.code)
    return StockMovementListItem(
        id=m.id,
        product_id=m.product_id,
        warehouse_id=m.warehouse_id,
        movement_type=m.movement_type.value
        if hasattr(m.movement_type, "value")
        else str(m.movement_type),
        quantity=m.quantity,
        performed_at=m.performed_at,
        created_at=m.created_at,
        product=product,
        warehouse=warehouse,
    )


def stock_movement_to_response(m: StockMovement) -> StockMovementResponse:
    """Build response from ORM without embedding Item/Warehouse (avoids lazy-load loops)."""

    product = None
    if getattr(m, "product", None) is not None:
        product = ProductInfo(name=m.product.item_name, code=m.product.item_code)
    warehouse = None
    if getattr(m, "warehouse", None) is not None:
        warehouse = WarehouseInfo(name=m.warehouse.name, code=m.warehouse.code)
    return StockMovementResponse(
        id=m.id,
        organization_id=m.organization_id,
        product_id=m.product_id,
        warehouse_id=m.warehouse_id,
        movement_type=m.movement_type.value
        if hasattr(m.movement_type, "value")
        else str(m.movement_type),
        quantity=m.quantity,
        unit_cost=m.unit_cost,
        reference_type=m.reference_type,
        reference_id=m.reference_id,
        notes=m.notes,
        performed_by=m.performed_by,
        performed_at=m.performed_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
        product=product,
        warehouse=warehouse,
    )
