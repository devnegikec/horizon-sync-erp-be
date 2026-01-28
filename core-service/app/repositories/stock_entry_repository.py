"""Stock entry and items repository"""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.base import StockEntryStatus, StockEntryType
from app.models.stock_entry import StockEntry, StockEntryItem


class StockEntryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict, items: list[dict]) -> StockEntry:
        entry = StockEntry(**data)
        self.db.add(entry)
        self.db.flush()
        for it in items:
            it["stock_entry_id"] = entry.id
            it["organization_id"] = entry.organization_id
            self.db.add(StockEntryItem(**it))
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def get_by_id(
        self, entry_id: UUID, organization_id: UUID, load_items: bool = True
    ) -> StockEntry | None:
        q = self.db.query(StockEntry).filter(
            StockEntry.id == entry_id,
            StockEntry.organization_id == organization_id,
        )
        if load_items:
            q = q.options(joinedload(StockEntry.items))
        return q.first()

    def get_by_no(
        self, stock_entry_no: str, organization_id: UUID
    ) -> StockEntry | None:
        return (
            self.db.query(StockEntry)
            .filter(
                StockEntry.stock_entry_no == stock_entry_no,
                StockEntry.organization_id == organization_id,
            )
            .first()
        )

    def update(self, entry: StockEntry, data: dict) -> StockEntry:
        for k, v in data.items():
            if hasattr(entry, k) and v is not None:
                setattr(entry, k, v)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def delete(self, entry: StockEntry) -> None:
        self.db.delete(entry)
        self.db.commit()

    def list_entries(
        self,
        organization_id: UUID,
        stock_entry_type: StockEntryType | None = None,
        status: StockEntryStatus | None = None,
        from_warehouse_id: UUID | None = None,
        to_warehouse_id: UUID | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "posting_date",
        sort_order: str = "desc",
    ) -> tuple[list[StockEntry], int]:
        q = self.db.query(StockEntry).filter(
            StockEntry.organization_id == organization_id
        )
        if stock_entry_type is not None:
            q = q.filter(StockEntry.stock_entry_type == stock_entry_type)
        if status is not None:
            q = q.filter(StockEntry.status == status)
        if from_warehouse_id is not None:
            q = q.filter(StockEntry.from_warehouse_id == from_warehouse_id)
        if to_warehouse_id is not None:
            q = q.filter(StockEntry.to_warehouse_id == to_warehouse_id)
        if search:
            t = f"%{search}%"
            q = q.filter(
                or_(StockEntry.stock_entry_no.ilike(t), StockEntry.remarks.ilike(t))
            )
        total = q.count()
        col = getattr(StockEntry, sort_by, StockEntry.posting_date)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    # ----- Items -----

    def get_item_by_id(
        self, item_id: UUID, organization_id: UUID
    ) -> StockEntryItem | None:
        return (
            self.db.query(StockEntryItem)
            .filter(
                StockEntryItem.id == item_id,
                StockEntryItem.organization_id == organization_id,
            )
            .first()
        )

    def add_item(self, data: dict) -> StockEntryItem:
        it = StockEntryItem(**data)
        self.db.add(it)
        self.db.commit()
        self.db.refresh(it)
        return it

    def update_item(self, it: StockEntryItem, data: dict) -> StockEntryItem:
        for k, v in data.items():
            if hasattr(it, k) and v is not None:
                setattr(it, k, v)
        self.db.commit()
        self.db.refresh(it)
        return it

    def delete_item(self, it: StockEntryItem) -> None:
        self.db.delete(it)
        self.db.commit()
