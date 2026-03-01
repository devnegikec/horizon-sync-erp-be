"""Invoice repository"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceItem


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
        self,
        invoice_id: UUID,
        organization_id: UUID,
        for_update: bool = False,
        load_items: bool = True,
    ) -> Invoice | None:
        """
        Get Invoice by ID, optionally with line items eagerly loaded.

        Args:
            invoice_id: Invoice ID
            organization_id: Organization ID
            for_update: If True, use SELECT FOR UPDATE to lock the row for concurrent updates
            load_items: If True, eager-load invoice items (default). Set False when the DB
                invoice_items table may not have all columns expected by the model (e.g. item_code).

        Returns:
            Invoice or None
        """
        from sqlalchemy.orm import joinedload

        query = self.db.query(Invoice).filter(
            Invoice.id == invoice_id,
            Invoice.organization_id == organization_id,
        )
        if load_items:
            query = query.options(joinedload(Invoice.items))

        if for_update:
            query = query.with_for_update()

        return query.first()

    def get_invoice_total_from_items(
        self, invoice_id: UUID, organization_id: UUID
    ) -> Decimal:
        """
        Sum line-item amounts for an invoice (only queries amount column).
        Use when invoice.total_amount is 0 but line items have amounts.
        """
        result = (
            self.db.query(func.coalesce(func.sum(InvoiceItem.amount), 0))
            .filter(
                InvoiceItem.invoice_id == invoice_id,
                InvoiceItem.organization_id == organization_id,
            )
            .scalar()
        )
        return Decimal(str(result)) if result is not None else Decimal("0")

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
            # API sends lowercase (sales/purchase); DB stores lowercase (sales/purchase)
            db_invoice_type = invoice_type.lower() if isinstance(invoice_type, str) else invoice_type
            q = q.filter(Invoice.invoice_type == db_invoice_type)
        total = q.count()
        # Map API sort field names to actual DB columns (grand_total, outstanding_amount are @property aliases)
        sort_column_map = {
            "posting_date": Invoice.posting_date,
            "grand_total": Invoice.grand_total,
            "outstanding_amount": Invoice.outstanding_amount,
        }
        col = sort_column_map.get(sort_by) or getattr(Invoice, sort_by, None)
        if col is None:
            col = Invoice.created_at
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
