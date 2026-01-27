"""ItemPrice service with business logic"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ItemNotFoundException, ItemPriceNotFoundException
from app.models.item_price import ItemPrice
from app.repositories.item_price_repository import ItemPriceRepository
from app.repositories.item_repository import ItemRepository
from app.schemas.item_price import ItemPriceCreate, ItemPriceUpdate


class ItemPriceService:
    """Service for item price operations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ItemPriceRepository(db)
        self.item_repo = ItemRepository(db)

    def create(self, data: ItemPriceCreate, organization_id: UUID) -> ItemPrice:
        """Create a new item price. Validates item exists."""
        if not self.item_repo.get_item_by_id(data.item_id, organization_id):
            raise ItemNotFoundException(f"Item with ID {data.item_id} not found")
        d = data.model_dump()
        d["organization_id"] = organization_id
        return self.repo.create(d)

    def get_by_id(self, price_id: UUID, organization_id: UUID) -> ItemPrice:
        """Get item price by ID. Raises ItemPriceNotFoundException if not found."""
        row = self.repo.get_by_id(price_id, organization_id)
        if not row:
            raise ItemPriceNotFoundException(f"Item price with ID {price_id} not found")
        return row

    def update(
        self, price_id: UUID, data: ItemPriceUpdate, organization_id: UUID
    ) -> ItemPrice:
        """Update an item price."""
        row = self.get_by_id(price_id, organization_id)
        return self.repo.update(row, data.model_dump(exclude_unset=True))

    def delete(self, price_id: UUID, organization_id: UUID) -> None:
        """Delete an item price."""
        row = self.get_by_id(price_id, organization_id)
        self.repo.delete(row)

    def get_list(
        self,
        organization_id: UUID,
        item_id: UUID | None = None,
        price_list_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[ItemPrice], dict]:
        """List item prices with pagination."""
        page_size = min(page_size, 100)
        items, total = self.repo.list_prices(
            organization_id=organization_id,
            item_id=item_id,
            price_list_id=price_list_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total_pages = (total + page_size - 1) // page_size if total else 1
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return items, pagination
