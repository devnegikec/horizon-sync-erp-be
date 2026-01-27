"""ItemSupplier repository for database operations"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.item_supplier import ItemSupplier


class ItemSupplierRepository:
    """Repository for item_supplier database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> ItemSupplier:
        """Create a new item supplier."""
        row = ItemSupplier(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_by_id(
        self, item_supplier_id: UUID, organization_id: UUID
    ) -> ItemSupplier | None:
        """Get item supplier by ID."""
        return (
            self.db.query(ItemSupplier)
            .filter(
                ItemSupplier.id == item_supplier_id,
                ItemSupplier.organization_id == organization_id,
            )
            .first()
        )

    def get_by_item_and_supplier(
        self, item_id: UUID, supplier_id: UUID, organization_id: UUID
    ) -> ItemSupplier | None:
        """Get by (item_id, supplier_id) for duplicate check."""
        return (
            self.db.query(ItemSupplier)
            .filter(
                ItemSupplier.item_id == item_id,
                ItemSupplier.supplier_id == supplier_id,
                ItemSupplier.organization_id == organization_id,
            )
            .first()
        )

    def update(self, row: ItemSupplier, data: dict) -> ItemSupplier:
        """Update item supplier fields."""
        for k, v in data.items():
            if hasattr(row, k):
                setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete(self, row: ItemSupplier) -> None:
        """Hard delete an item supplier."""
        self.db.delete(row)
        self.db.commit()

    def list_item_suppliers(
        self,
        organization_id: UUID,
        item_id: UUID | None = None,
        supplier_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[ItemSupplier], int]:
        """List item suppliers with filters and pagination."""
        q = self.db.query(ItemSupplier).filter(
            ItemSupplier.organization_id == organization_id
        )
        if item_id:
            q = q.filter(ItemSupplier.item_id == item_id)
        if supplier_id is not None:
            q = q.filter(ItemSupplier.supplier_id == supplier_id)
        total = q.count()
        col = getattr(ItemSupplier, sort_by, ItemSupplier.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total
