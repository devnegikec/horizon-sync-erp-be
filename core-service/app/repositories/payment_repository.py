"""Payment repository"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Payment:
        p = Payment(**data)
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p

    def get_by_id(self, payment_id: UUID, organization_id: UUID) -> Payment | None:
        return (
            self.db.query(Payment)
            .filter(
                Payment.id == payment_id,
                Payment.organization_id == organization_id,
            )
            .first()
        )

    def list_payments(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        party_id: UUID | None = None,
        status: str | None = None,
        payment_type: str | None = None,
        sort_by: str = "posting_date",
        sort_order: str = "desc",
    ) -> tuple[list[Payment], int]:
        q = self.db.query(Payment).filter(Payment.organization_id == organization_id)
        if party_id is not None:
            q = q.filter(Payment.party_id == party_id)
        if status is not None:
            q = q.filter(Payment.status == status)
        if payment_type is not None:
            q = q.filter(Payment.payment_type == payment_type)
        total = q.count()
        col = getattr(Payment, sort_by, Payment.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, p: Payment, data: dict) -> Payment:
        for k, v in data.items():
            if hasattr(p, k):
                setattr(p, k, v)
        self.db.commit()
        self.db.refresh(p)
        return p

    def delete(self, p: Payment) -> None:
        self.db.delete(p)
        self.db.commit()
