"""Stock reconciliation and items service"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateReconciliationNoException,
    StockReconciliationItemNotFoundException,
    StockReconciliationNotFoundException,
)
from app.models.base import StockEntryStatus
from app.models.stock_reconciliation import StockReconciliation, StockReconciliationItem
from app.repositories.stock_reconciliation_repository import (
    StockReconciliationRepository,
)
from app.schemas.stock_reconciliation import (
    StockReconciliationCreate,
    StockReconciliationItemCreate,
    StockReconciliationItemUpdate,
    StockReconciliationUpdate,
)


def _enum(s: str | None, cls, default=None):
    if not s:
        return default
    try:
        return cls(str(s).lower())
    except (ValueError, KeyError):
        return default


class StockReconciliationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StockReconciliationRepository(db)

    def create(
        self, data: StockReconciliationCreate, organization_id: UUID, user_id: UUID
    ) -> StockReconciliation:
        # Auto-generate reconciliation_no if not provided
        if not data.reconciliation_no:
            from app.services.document_numbering_service import DocumentNumberingService

            data.reconciliation_no = DocumentNumberingService(self.db).get_next_number(
                organization_id, "stock_reconciliation"
            )

        if self.repo.get_by_no(data.reconciliation_no, organization_id):
            raise DuplicateReconciliationNoException(
                f"Reconciliation with number '{data.reconciliation_no}' already exists"
            )
        h = data.model_dump(exclude={"items"})
        h["organization_id"] = organization_id
        h["created_by"] = user_id
        h["updated_by"] = user_id
        h["status"] = _enum(h.get("status"), StockEntryStatus) or StockEntryStatus.DRAFT
        items = []
        for i in data.items:
            it = i.model_dump()
            it["organization_id"] = organization_id
            if it.get("current_qty") is not None and it.get("qty") is not None:
                it["qty_difference"] = Decimal(str(it["qty"])) - Decimal(
                    str(it["current_qty"])
                )
            items.append(it)
        rec = self.repo.create(h, items)
        return rec

    def get_by_id(
        self, rec_id: UUID, organization_id: UUID, load_items: bool = True
    ) -> StockReconciliation:
        r = self.repo.get_by_id(rec_id, organization_id, load_items=load_items)
        if not r:
            raise StockReconciliationNotFoundException(
                f"Stock reconciliation with ID {rec_id} not found"
            )
        return r

    def update(
        self,
        rec_id: UUID,
        data: StockReconciliationUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> StockReconciliation:
        r = self.get_by_id(rec_id, organization_id)
        d = data.model_dump(exclude_unset=True)
        d["updated_by"] = user_id
        if d.get("status") is not None:
            d["status"] = _enum(d["status"], StockEntryStatus)
        return self.repo.update(r, d)

    def delete(self, rec_id: UUID, organization_id: UUID) -> None:
        r = self.get_by_id(rec_id, organization_id)
        if r.status != StockEntryStatus.DRAFT:
            from app.core.exceptions import CannotDeleteException

            raise CannotDeleteException("Only draft reconciliations can be deleted")
        self.repo.delete(r)

    def get_list(
        self,
        organization_id: UUID,
        status: str | None = None,
        warehouse_id: UUID | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "posting_date",
        sort_order: str = "desc",
    ) -> tuple[list[StockReconciliation], dict]:
        page_size = min(page_size, 100)
        status_enum = _enum(status, StockEntryStatus) if status else None
        items, total = self.repo.list_reconciliations(
            organization_id=organization_id,
            status=status_enum,
            warehouse_id=warehouse_id,
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
        rec_id: UUID,
        data: StockReconciliationItemCreate,
        organization_id: UUID,
    ) -> StockReconciliationItem:
        r = self.get_by_id(rec_id, organization_id)
        if r.status != StockEntryStatus.DRAFT:
            from app.core.exceptions import CannotDeleteException

            raise CannotDeleteException(
                "Items can only be added to draft reconciliations"
            )
        d = data.model_dump()
        d["organization_id"] = organization_id
        d["reconciliation_id"] = rec_id
        if d.get("current_qty") is not None and d.get("qty") is not None:
            d["qty_difference"] = Decimal(str(d["qty"])) - Decimal(
                str(d["current_qty"])
            )
        return self.repo.add_item(d)

    def update_item(
        self,
        rec_id: UUID,
        item_id: UUID,
        data: StockReconciliationItemUpdate,
        organization_id: UUID,
    ) -> StockReconciliationItem:
        r = self.get_by_id(rec_id, organization_id)
        if r.status != StockEntryStatus.DRAFT:
            from app.core.exceptions import CannotDeleteException

            raise CannotDeleteException(
                "Items can only be updated in draft reconciliations"
            )
        it = self.repo.get_item_by_id(item_id, organization_id)
        if not it or it.reconciliation_id != rec_id:
            raise StockReconciliationItemNotFoundException(
                f"Reconciliation item with ID {item_id} not found"
            )
        return self.repo.update_item(it, data.model_dump(exclude_unset=True))

    def delete_item(self, rec_id: UUID, item_id: UUID, organization_id: UUID) -> None:
        r = self.get_by_id(rec_id, organization_id)
        if r.status != StockEntryStatus.DRAFT:
            from app.core.exceptions import CannotDeleteException

            raise CannotDeleteException(
                "Items can only be removed from draft reconciliations"
            )
        it = self.repo.get_item_by_id(item_id, organization_id)
        if not it or it.reconciliation_id != rec_id:
            raise StockReconciliationItemNotFoundException(
                f"Reconciliation item with ID {item_id} not found"
            )
        self.repo.delete_item(it)
