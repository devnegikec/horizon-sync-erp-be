"""Invoice repository"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.invoice import Invoice


class InvoiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Invoice:
        inv = Invoice(**data)
        self.db.add(inv)
        self.db.commit()
        self.db.refresh(inv)
        return inv

    def get_by_id(
        self, invoice_id: UUID, organization_id: UUID, for_update: bool = False
    ) -> Invoice | None:
        """
        Get Invoice by ID with items and customer eagerly loaded.

        Args:
            invoice_id: Invoice ID
            organization_id: Organization ID
            for_update: If True, use SELECT FOR UPDATE to lock the row for concurrent updates

        Returns:
            Invoice or None
        """
        from sqlalchemy.orm import joinedload

        query = (
            self.db.query(Invoice)
            .options(joinedload(Invoice.items))
            .filter(
                Invoice.id == invoice_id,
                Invoice.organization_id == organization_id,
            )
        )

        if for_update:
            query = query.with_for_update()

        return query.first()

    def list_invoices(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        party_id: UUID | None = None,
        status: str | None = None,
        invoice_type: str | None = None,
        sort_by: str = "posting_date",
        sort_order: str = "desc",
    ) -> tuple[list[Invoice], int]:
        q = self.db.query(Invoice).filter(Invoice.organization_id == organization_id)
        if party_id is not None:
            q = q.filter(Invoice.party_id == party_id)
        if status is not None:
            q = q.filter(Invoice.status == status)
        if invoice_type is not None:
            q = q.filter(Invoice.invoice_type == invoice_type)
        total = q.count()
        col = getattr(Invoice, sort_by, Invoice.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, inv: Invoice, data: dict) -> Invoice:
        for k, v in data.items():
            if hasattr(inv, k):
                setattr(inv, k, v)
        self.db.commit()
        self.db.refresh(inv)
        return inv

    def delete(self, inv: Invoice) -> None:
        self.db.delete(inv)
        self.db.commit()
