"""Stock movement service - append-only log"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import StockMovementNotFoundException
from app.models.base import MovementType
from app.models.stock_movement import StockMovement
from app.repositories.stock_movement_repository import StockMovementRepository
from app.schemas.stock_movement import StockMovementCreate


def _enum(s: str | None, cls, default=None):
    if not s:
        return default
    try:
        return cls(str(s).lower())
    except (ValueError, KeyError):
        return default


class StockMovementService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StockMovementRepository(db)

    def create(
        self,
        data: StockMovementCreate,
        organization_id: UUID,
        user_id: UUID | None = None,
    ) -> StockMovement:
        d = data.model_dump()
        d["organization_id"] = organization_id
        d["product_id"] = d.pop("item_id")
        d["movement_type"] = (
            _enum(d.get("movement_type"), MovementType) or MovementType.IN
        )
        d["performed_by"] = user_id
        if d.get("performed_at") is None:
            d["performed_at"] = datetime.now(UTC)
        return self.repo.create(d)

    def get_by_id(self, movement_id: UUID, organization_id: UUID) -> StockMovement:
        m = self.repo.get_by_id(movement_id, organization_id)
        if not m:
            raise StockMovementNotFoundException(
                f"Stock movement with ID {movement_id} not found"
            )
        return m

    def get_list(
        self,
        organization_id: UUID,
        product_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        movement_type: str | None = None,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "performed_at",
        sort_order: str = "desc",
    ) -> tuple[list[StockMovement], dict]:
        page_size = min(page_size, 100)
        type_enum = _enum(movement_type, MovementType) if movement_type else None
        items, total = self.repo.list_movements(
            organization_id=organization_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            movement_type=type_enum,
            reference_type=reference_type,
            reference_id=reference_id,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        tp = (total + page_size - 1) // page_size
        return items, {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": tp,
            "has_next": page < tp,
            "has_prev": page > 1,
        }
