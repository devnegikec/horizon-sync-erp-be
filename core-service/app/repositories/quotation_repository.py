"""Quotation repository"""

from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.item import Item
from app.models.quotation import Quotation, QuotationItem


class QuotationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Quotation:
        quotation = Quotation(**data)
        self.db.add(quotation)
        self.db.commit()
        self.db.refresh(quotation)
        return quotation

    def get_by_id(self, quotation_id: UUID, organization_id: UUID) -> Quotation | None:
        return (
            self.db.query(Quotation)
            .options(
                joinedload(Quotation.customer),
                joinedload(Quotation.items)
                .joinedload(QuotationItem.item)
                .joinedload(Item.item_group),
            )
            .filter(
                Quotation.id == quotation_id,
                Quotation.organization_id == organization_id,
            )
            .first()
        )

    def list_quotations(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        customer_id: UUID | None = None,
        status: str | None = None,
        sort_by: str = "quotation_date",
        sort_order: str = "desc",
    ) -> tuple[list[Quotation], int]:
        q = (
            self.db.query(Quotation)
            .options(joinedload(Quotation.customer))
            .filter(Quotation.organization_id == organization_id)
        )
        if customer_id is not None:
            q = q.filter(Quotation.customer_id == customer_id)
        if status is not None:
            q = q.filter(Quotation.status == status)
        total = q.count()
        col = getattr(Quotation, sort_by, Quotation.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, quotation: Quotation, data: dict) -> Quotation:
        for k, v in data.items():
            if hasattr(quotation, k):
                setattr(quotation, k, v)
        self.db.commit()
        self.db.refresh(quotation)
        return quotation

    def delete(self, quotation: Quotation) -> None:
        self.db.delete(quotation)
        self.db.commit()

    def count_by_year(self, organization_id: UUID, year: int) -> int:
        """Count quotations for a given organization and year"""
        from sqlalchemy import extract, func

        return (
            self.db.query(func.count(Quotation.id))
            .filter(
                Quotation.organization_id == organization_id,
                extract("year", Quotation.created_at) == year,
            )
            .scalar()
            or 0
        )
