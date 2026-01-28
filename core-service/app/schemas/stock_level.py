"""Stock level schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import PaginationMeta


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

    model_config = ConfigDict(from_attributes=True)


class StockLevelListResponse(BaseModel):
    stock_levels: list[StockLevelListItem]
    pagination: PaginationMeta
