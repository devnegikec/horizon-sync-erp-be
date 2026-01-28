"""Stock movement schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


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

    model_config = ConfigDict(from_attributes=True)


class StockMovementListItem(BaseModel):
    id: UUID
    product_id: UUID
    warehouse_id: UUID
    movement_type: str
    quantity: int
    performed_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockMovementListResponse(BaseModel):
    stock_movements: list[StockMovementListItem]
    pagination: PaginationMeta
