"""RFQ repository"""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.rfq import RFQ, RFQLine, RFQSupplier, SupplierQuote


class RFQRepository:
    """Repository for RFQ operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> RFQ:
        """Create a new RFQ"""
        rfq = RFQ(**data)
        self.db.add(rfq)
        self.db.commit()
        self.db.refresh(rfq)
        return rfq

    def get_by_id(self, rfq_id: UUID, organization_id: UUID) -> RFQ | None:
        """Get RFQ by ID with all relationships"""
        return (
            self.db.query(RFQ)
            .options(
                joinedload(RFQ.line_items).joinedload(RFQLine.quotes),
                joinedload(RFQ.suppliers),
            )
            .filter(
                RFQ.id == rfq_id,
                RFQ.organization_id == organization_id,
                RFQ.deleted_at.is_(None),
            )
            .first()
        )

    def list_rfqs(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: str | None = None,
    ) -> tuple[list[RFQ], int]:
        """List RFQs with pagination"""
        q = self.db.query(RFQ).filter(
            RFQ.organization_id == organization_id,
            RFQ.deleted_at.is_(None),
        )

        if status is not None:
            q = q.filter(RFQ.status == status)

        total = q.count()

        col = getattr(RFQ, sort_by, RFQ.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())

        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, rfq: RFQ, data: dict) -> RFQ:
        """Update RFQ"""
        for k, v in data.items():
            if hasattr(rfq, k):
                setattr(rfq, k, v)
        self.db.commit()
        self.db.refresh(rfq)
        return rfq

    def delete(self, rfq: RFQ) -> None:
        """Delete RFQ"""
        self.db.delete(rfq)
        self.db.commit()

    def create_line_item(self, data: dict) -> RFQLine:
        """Create an RFQ line item"""
        line_item = RFQLine(**data)
        self.db.add(line_item)
        self.db.commit()
        self.db.refresh(line_item)
        return line_item

    def delete_line_items(self, rfq_id: UUID) -> None:
        """Delete all line items for an RFQ"""
        self.db.query(RFQLine).filter(RFQLine.rfq_id == rfq_id).delete()
        self.db.commit()

    def get_line_items_count(self, rfq_id: UUID) -> int:
        """Get count of line items for an RFQ"""
        return (
            self.db.query(func.count(RFQLine.id))
            .filter(RFQLine.rfq_id == rfq_id)
            .scalar()
        )

    def create_supplier(self, data: dict) -> RFQSupplier:
        """Create an RFQ supplier association"""
        supplier = RFQSupplier(**data)
        self.db.add(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    def delete_suppliers(self, rfq_id: UUID) -> None:
        """Delete all suppliers for an RFQ"""
        self.db.query(RFQSupplier).filter(RFQSupplier.rfq_id == rfq_id).delete()
        self.db.commit()

    def get_suppliers_count(self, rfq_id: UUID) -> int:
        """Get count of suppliers for an RFQ"""
        return (
            self.db.query(func.count(RFQSupplier.id))
            .filter(RFQSupplier.rfq_id == rfq_id)
            .scalar()
        )

    def create_quote(self, data: dict) -> SupplierQuote:
        """Create a supplier quote"""
        quote = SupplierQuote(**data)
        self.db.add(quote)
        self.db.commit()
        self.db.refresh(quote)
        return quote

    def get_quote(
        self, rfq_line_id: UUID, supplier_id: UUID, organization_id: UUID
    ) -> SupplierQuote | None:
        """Get a specific supplier quote"""
        return (
            self.db.query(SupplierQuote)
            .filter(
                SupplierQuote.rfq_line_id == rfq_line_id,
                SupplierQuote.supplier_id == supplier_id,
                SupplierQuote.organization_id == organization_id,
            )
            .first()
        )

    def update_quote(self, quote: SupplierQuote, data: dict) -> SupplierQuote:
        """Update a supplier quote"""
        for k, v in data.items():
            if hasattr(quote, k):
                setattr(quote, k, v)
        self.db.commit()
        self.db.refresh(quote)
        return quote
