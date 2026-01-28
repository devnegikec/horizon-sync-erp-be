"""ItemPrice repository for database operations"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.item_price import ItemPrice


class ItemPriceRepository:
    """Repository for item_price database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> ItemPrice:
        """Create a new item price."""
        row = ItemPrice(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_by_id(self, price_id: UUID, organization_id: UUID) -> ItemPrice | None:
        """Get item price by ID."""
        return (
            self.db.query(ItemPrice)
            .filter(
                ItemPrice.id == price_id,
                ItemPrice.organization_id == organization_id,
            )
            .first()
        )

    def update(self, row: ItemPrice, data: dict) -> ItemPrice:
        """Update item price fields."""
        for k, v in data.items():
            if hasattr(row, k):
                setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete(self, row: ItemPrice) -> None:
        """Hard delete an item price."""
        self.db.delete(row)
        self.db.commit()

    def list_prices(
        self,
        organization_id: UUID,
        item_id: UUID | None = None,
        price_list_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[ItemPrice], int]:
        """List item prices with filters and pagination."""
        q = self.db.query(ItemPrice).filter(
            ItemPrice.organization_id == organization_id
        )
        if item_id:
            q = q.filter(ItemPrice.item_id == item_id)
        if price_list_id is not None:
            q = q.filter(ItemPrice.price_list_id == price_list_id)
        total = q.count()
        col = getattr(ItemPrice, sort_by, ItemPrice.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total
