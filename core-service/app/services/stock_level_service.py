"""Stock level service - get or create/update levels"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import StockLevelNotFoundException
from app.models.stock_level import StockLevel
from app.repositories.stock_level_repository import StockLevelRepository
from app.schemas.stock_level import StockLevelCreate, StockLevelUpdate


def _avail(on_hand: int, reserved: int) -> int:
    return max(0, (on_hand or 0) - (reserved or 0))


class StockLevelService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StockLevelRepository(db)

    def get_or_create(
        self, item_id: UUID, warehouse_id: UUID, organization_id: UUID
    ) -> StockLevel:
        """Get existing level or create with zeros."""
        s = self.repo.get_by_product_warehouse(item_id, warehouse_id, organization_id)
        if s:
            return s
        return self.repo.create(
            {
                "organization_id": organization_id,
                "product_id": item_id,
                "warehouse_id": warehouse_id,
                "quantity_on_hand": 0,
                "quantity_reserved": 0,
                "quantity_available": 0,
            }
        )

    def get_by_id(self, level_id: UUID, organization_id: UUID) -> StockLevel:
        s = self.repo.get_by_id(level_id, organization_id)
        if not s:
            raise StockLevelNotFoundException(
                f"Stock level with ID {level_id} not found"
            )
        return s

    def get(
        self, item_id: UUID, warehouse_id: UUID, organization_id: UUID
    ) -> StockLevel:
        s = self.repo.get_by_product_warehouse(item_id, warehouse_id, organization_id)
        if not s:
            raise StockLevelNotFoundException(
                f"No stock level for item {item_id} in warehouse {warehouse_id}"
            )
        return s

    def create(self, data: StockLevelCreate, organization_id: UUID) -> StockLevel:
        existing = self.repo.get_by_product_warehouse(
            data.item_id, data.warehouse_id, organization_id
        )
        if existing:
            # upsert: update
            on_hand = data.quantity_on_hand
            reserved = data.quantity_reserved
            avail = (
                data.quantity_available
                if data.quantity_available is not None
                else _avail(on_hand, reserved)
            )
            return self.repo.update(
                existing,
                {
                    "quantity_on_hand": on_hand,
                    "quantity_reserved": reserved,
                    "quantity_available": avail,
                    "last_counted_at": data.last_counted_at,
                },
            )
        avail = (
            data.quantity_available
            if data.quantity_available is not None
            else _avail(data.quantity_on_hand, data.quantity_reserved)
        )
        return self.repo.create(
            {
                "organization_id": organization_id,
                "product_id": data.item_id,
                "warehouse_id": data.warehouse_id,
                "quantity_on_hand": data.quantity_on_hand,
                "quantity_reserved": data.quantity_reserved,
                "quantity_available": avail,
                "last_counted_at": data.last_counted_at,
            }
        )

    def update(
        self,
        item_id: UUID,
        warehouse_id: UUID,
        data: StockLevelUpdate,
        organization_id: UUID,
    ) -> StockLevel:
        s = self.get(item_id, warehouse_id, organization_id)
        d = data.model_dump(exclude_unset=True)
        if "quantity_on_hand" in d or "quantity_reserved" in d:
            on_hand = d.get("quantity_on_hand", s.quantity_on_hand)
            reserved = d.get("quantity_reserved", s.quantity_reserved)
            if "quantity_available" not in d:
                d["quantity_available"] = _avail(on_hand or 0, reserved or 0)
        return self.repo.update(s, d)

    def update_by_id(
        self, level_id: UUID, data: StockLevelUpdate, organization_id: UUID
    ) -> StockLevel:
        s = self.get_by_id(level_id, organization_id)
        d = data.model_dump(exclude_unset=True)
        if "quantity_on_hand" in d or "quantity_reserved" in d:
            on_hand = d.get("quantity_on_hand", s.quantity_on_hand)
            reserved = d.get("quantity_reserved", s.quantity_reserved)
            if "quantity_available" not in d:
                d["quantity_available"] = _avail(on_hand or 0, reserved or 0)
        return self.repo.update(s, d)

    def get_list(
        self,
        organization_id: UUID,
        product_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> tuple[list[StockLevel], dict]:
        page_size = min(page_size, 100)
        items, total = self.repo.list_levels(
            organization_id=organization_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
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
