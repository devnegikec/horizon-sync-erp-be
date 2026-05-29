"""Stock reconciliation and items repository"""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.base import StockEntryStatus
from app.models.stock_reconciliation import StockReconciliation, StockReconciliationItem


class StockReconciliationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict, items: list[dict]) -> StockReconciliation:
        rec = StockReconciliation(**data)
        self.db.add(rec)
        self.db.flush()
        for it in items:
            it["reconciliation_id"] = rec.id
            it["organization_id"] = rec.organization_id
            self.db.add(StockReconciliationItem(**it))
        self.db.commit()
        self.db.refresh(rec)
        return rec

    def get_by_id(
        self, rec_id: UUID, organization_id: UUID, load_items: bool = True
    ) -> StockReconciliation | None:
        q = self.db.query(StockReconciliation).filter(
            StockReconciliation.id == rec_id,
            StockReconciliation.organization_id == organization_id,
        )
        if load_items:
            q = q.options(joinedload(StockReconciliation.items))
        return q.first()

    def get_by_no(
        self, reconciliation_no: str, organization_id: UUID
    ) -> StockReconciliation | None:
        return (
            self.db.query(StockReconciliation)
            .filter(
                StockReconciliation.reconciliation_no == reconciliation_no,
                StockReconciliation.organization_id == organization_id,
            )
            .first()
        )

    def update(self, rec: StockReconciliation, data: dict) -> StockReconciliation:
        for k, v in data.items():
            if hasattr(rec, k) and v is not None:
                setattr(rec, k, v)
        self.db.commit()
        self.db.refresh(rec)
        return rec

    def delete(self, rec: StockReconciliation) -> None:
        self.db.delete(rec)
        self.db.commit()

    def list_reconciliations(
        self,
        organization_id: UUID,
        status: StockEntryStatus | None = None,
        warehouse_id: UUID | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "posting_date",
        sort_order: str = "desc",
    ) -> tuple[list[StockReconciliation], int]:
        q = self.db.query(StockReconciliation).filter(
            StockReconciliation.organization_id == organization_id
        )
        if status is not None:
            q = q.filter(StockReconciliation.status == status)
        if warehouse_id is not None:
            q = q.filter(
                StockReconciliation.id.in_(
                    self.db.query(StockReconciliationItem.reconciliation_id).filter(
                        StockReconciliationItem.warehouse_id == warehouse_id
                    )
                )
            )
        if search:
            t = f"%{search}%"
            q = q.filter(
                or_(
                    StockReconciliation.reconciliation_no.ilike(t),
                    StockReconciliation.remarks.ilike(t),
                )
            )
        total = q.count()
        col = getattr(StockReconciliation, sort_by, StockReconciliation.posting_date)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def get_item_by_id(
        self, item_id: UUID, organization_id: UUID
    ) -> StockReconciliationItem | None:
        return (
            self.db.query(StockReconciliationItem)
            .filter(
                StockReconciliationItem.id == item_id,
                StockReconciliationItem.organization_id == organization_id,
            )
            .first()
        )

    def add_item(self, data: dict) -> StockReconciliationItem:
        it = StockReconciliationItem(**data)
        self.db.add(it)
        self.db.commit()
        self.db.refresh(it)
        return it

    def update_item(
        self, it: StockReconciliationItem, data: dict
    ) -> StockReconciliationItem:
        for k, v in data.items():
            if hasattr(it, k) and v is not None:
                setattr(it, k, v)
        self.db.commit()
        self.db.refresh(it)
        return it

    def delete_item(self, it: StockReconciliationItem) -> None:
        self.db.delete(it)
        self.db.commit()
