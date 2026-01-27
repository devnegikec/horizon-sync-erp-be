"""Stock entry and items service"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateStockEntryNoException,
    StockEntryItemNotFoundException,
    StockEntryNotFoundException,
)
from app.models.base import StockEntryStatus, StockEntryType
from app.models.stock_entry import StockEntry, StockEntryItem
from app.repositories.stock_entry_repository import StockEntryRepository
from app.schemas.stock_entry import (
    StockEntryCreate,
    StockEntryItemCreate,
    StockEntryItemUpdate,
    StockEntryUpdate,
)


def _enum(s: str | None, enum_cls, default=None):
    if not s:
        return default
    try:
        return enum_cls(str(s).lower())
    except (ValueError, KeyError):
        return default


def _item_dict(d: StockEntryItemCreate) -> dict:
    m = d.model_dump()
    br = m.get("basic_rate")
    qty = m.get("qty")
    if br is not None and qty is not None:
        m["basic_amount"] = Decimal(str(br)) * Decimal(str(qty))
    return m


class StockEntryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StockEntryRepository(db)

    def create(
        self, data: StockEntryCreate, organization_id: UUID, user_id: UUID
    ) -> StockEntry:
        if self.repo.get_by_no(data.stock_entry_no, organization_id):
            raise DuplicateStockEntryNoException(
                f"Stock entry with number '{data.stock_entry_no}' already exists"
            )
        h = data.model_dump(exclude={"items"})
        h["organization_id"] = organization_id
        h["created_by"] = user_id
        h["updated_by"] = user_id
        h["stock_entry_type"] = (
            _enum(h.get("stock_entry_type"), StockEntryType)
            or StockEntryType.MATERIAL_RECEIPT
        )
        h["status"] = _enum(h.get("status"), StockEntryStatus) or StockEntryStatus.DRAFT
        items = [_item_dict(i) for i in data.items]
        return self.repo.create(h, items)

    def get_by_id(
        self, entry_id: UUID, organization_id: UUID, load_items: bool = True
    ) -> StockEntry:
        e = self.repo.get_by_id(entry_id, organization_id, load_items=load_items)
        if not e:
            raise StockEntryNotFoundException(
                f"Stock entry with ID {entry_id} not found"
            )
        return e

    def update(
        self,
        entry_id: UUID,
        data: StockEntryUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> StockEntry:
        e = self.get_by_id(entry_id, organization_id)
        d = data.model_dump(exclude_unset=True)
        d["updated_by"] = user_id
        if d.get("stock_entry_type"):
            d["stock_entry_type"] = _enum(d["stock_entry_type"], StockEntryType)
        if d.get("status") is not None:
            d["status"] = _enum(d["status"], StockEntryStatus)
        return self.repo.update(e, d)

    def delete(self, entry_id: UUID, organization_id: UUID) -> None:
        e = self.get_by_id(entry_id, organization_id)
        if e.status != StockEntryStatus.DRAFT:
            from app.core.exceptions import CannotDeleteException

            raise CannotDeleteException("Only draft stock entries can be deleted")
        self.repo.delete(e)

    def get_list(
        self,
        organization_id: UUID,
        stock_entry_type: str | None = None,
        status: str | None = None,
        from_warehouse_id: UUID | None = None,
        to_warehouse_id: UUID | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "posting_date",
        sort_order: str = "desc",
    ) -> tuple[list[StockEntry], dict]:
        page_size = min(page_size, 100)
        type_enum = (
            _enum(stock_entry_type, StockEntryType) if stock_entry_type else None
        )
        status_enum = _enum(status, StockEntryStatus) if status else None
        items, total = self.repo.list_entries(
            organization_id=organization_id,
            stock_entry_type=type_enum,
            status=status_enum,
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
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

    def add_item(
        self,
        entry_id: UUID,
        data: StockEntryItemCreate,
        organization_id: UUID,
    ) -> StockEntryItem:
        e = self.get_by_id(entry_id, organization_id)
        if e.status != StockEntryStatus.DRAFT:
            from app.core.exceptions import CannotDeleteException

            raise CannotDeleteException(
                "Items can only be added to draft stock entries"
            )
        d = _item_dict(data)
        d["organization_id"] = organization_id
        d["stock_entry_id"] = entry_id
        return self.repo.add_item(d)

    def update_item(
        self,
        entry_id: UUID,
        item_id: UUID,
        data: StockEntryItemUpdate,
        organization_id: UUID,
    ) -> StockEntryItem:
        e = self.get_by_id(entry_id, organization_id)
        if e.status != StockEntryStatus.DRAFT:
            from app.core.exceptions import CannotDeleteException

            raise CannotDeleteException(
                "Items can only be updated in draft stock entries"
            )
        it = self.repo.get_item_by_id(item_id, organization_id)
        if not it or it.stock_entry_id != entry_id:
            raise StockEntryItemNotFoundException(
                f"Stock entry item with ID {item_id} not found"
            )
        d = data.model_dump(exclude_unset=True)
        return self.repo.update_item(it, d)

    def delete_item(self, entry_id: UUID, item_id: UUID, organization_id: UUID) -> None:
        e = self.get_by_id(entry_id, organization_id)
        if e.status != StockEntryStatus.DRAFT:
            from app.core.exceptions import CannotDeleteException

            raise CannotDeleteException(
                "Items can only be removed from draft stock entries"
            )
        it = self.repo.get_item_by_id(item_id, organization_id)
        if not it or it.stock_entry_id != entry_id:
            raise StockEntryItemNotFoundException(
                f"Stock entry item with ID {item_id} not found"
            )
        self.repo.delete_item(it)
