"""ItemSupplier service with business logic"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateItemSupplierException,
    ItemNotFoundException,
    ItemSupplierNotFoundException,
    SupplierNotFoundException,
)
from app.models.item_supplier import ItemSupplier
from app.repositories.item_repository import ItemRepository
from app.repositories.item_supplier_repository import ItemSupplierRepository
from app.repositories.supplier_repository import SupplierRepository
from app.schemas.item_supplier import ItemSupplierCreate, ItemSupplierUpdate


class ItemSupplierService:
    """Service for item supplier operations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ItemSupplierRepository(db)
        self.item_repo = ItemRepository(db)
        self.supplier_repo = SupplierRepository(db)

    def create(self, data: ItemSupplierCreate, organization_id: UUID) -> ItemSupplier:
        """Create a new item supplier. Validates item and supplier exist; rejects duplicate (item_id, supplier_id)."""
        if not self.item_repo.get_item_by_id(data.item_id, organization_id):
            raise ItemNotFoundException(f"Item with ID {data.item_id} not found")
        if not self.supplier_repo.get_supplier_by_id(data.supplier_id, organization_id):
            raise SupplierNotFoundException(
                f"Supplier with ID {data.supplier_id} not found"
            )
        if self.repo.get_by_item_and_supplier(
            data.item_id, data.supplier_id, organization_id
        ):
            raise DuplicateItemSupplierException(
                f"Item-supplier link already exists for item {data.item_id} and supplier {data.supplier_id}"
            )
        d = data.model_dump()
        d["organization_id"] = organization_id
        return self.repo.create(d)

    def get_by_id(self, item_supplier_id: UUID, organization_id: UUID) -> ItemSupplier:
        """Get item supplier by ID. Raises ItemSupplierNotFoundException if not found."""
        row = self.repo.get_by_id(item_supplier_id, organization_id)
        if not row:
            raise ItemSupplierNotFoundException(
                f"Item supplier with ID {item_supplier_id} not found"
            )
        return row

    def update(
        self,
        item_supplier_id: UUID,
        data: ItemSupplierUpdate,
        organization_id: UUID,
    ) -> ItemSupplier:
        """Update an item supplier."""
        row = self.get_by_id(item_supplier_id, organization_id)
        return self.repo.update(row, data.model_dump(exclude_unset=True))

    def delete(self, item_supplier_id: UUID, organization_id: UUID) -> None:
        """Delete an item supplier."""
        row = self.get_by_id(item_supplier_id, organization_id)
        self.repo.delete(row)

    def get_list(
        self,
        organization_id: UUID,
        item_id: UUID | None = None,
        supplier_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[ItemSupplier], dict]:
        """List item suppliers with pagination."""
        page_size = min(page_size, 100)
        items, total = self.repo.list_item_suppliers(
            organization_id=organization_id,
            item_id=item_id,
            supplier_id=supplier_id,
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
