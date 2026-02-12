"""Delivery note repository"""

from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.customer import Customer
from app.models.delivery_note import DeliveryNote, DeliveryNoteItem
from app.models.warehouse import Warehouse


class DeliveryNoteRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict, items: list[dict]) -> DeliveryNote:
        dn = DeliveryNote(**data)
        self.db.add(dn)
        self.db.flush()
        for it in items:
            it["delivery_note_id"] = dn.id
            it["organization_id"] = dn.organization_id
            self.db.add(DeliveryNoteItem(**it))
        self.db.commit()
        self.db.refresh(dn)
        return dn

    def get_by_id(
        self, delivery_note_id: UUID, organization_id: UUID, load_items: bool = True
    ) -> DeliveryNote | None:
        q = (
            self.db.query(DeliveryNote)
            .outerjoin(Customer, DeliveryNote.customer_id == Customer.id)
            .outerjoin(Warehouse, DeliveryNote.warehouse_id == Warehouse.id)
            .filter(
                DeliveryNote.id == delivery_note_id,
                DeliveryNote.organization_id == organization_id,
            )
        )
        if load_items:
            q = q.options(joinedload(DeliveryNote.items))
        dn = q.first()
        return dn

    def get_by_no(
        self, delivery_note_no: str, organization_id: UUID
    ) -> DeliveryNote | None:
        return (
            self.db.query(DeliveryNote)
            .filter(
                DeliveryNote.delivery_note_no == delivery_note_no,
                DeliveryNote.organization_id == organization_id,
            )
            .first()
        )

    def list_delivery_notes(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        customer_id: UUID | None = None,
        status: str | None = None,
        sort_by: str = "delivery_date",
        sort_order: str = "desc",
    ) -> tuple[list[DeliveryNote], int]:
        q = (
            self.db.query(DeliveryNote)
            .outerjoin(Customer, DeliveryNote.customer_id == Customer.id)
            .outerjoin(Warehouse, DeliveryNote.warehouse_id == Warehouse.id)
            .filter(DeliveryNote.organization_id == organization_id)
        )
        if customer_id is not None:
            q = q.filter(DeliveryNote.customer_id == customer_id)
        if status is not None:
            q = q.filter(DeliveryNote.status == status)
        total = q.count()
        col = getattr(DeliveryNote, sort_by, DeliveryNote.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, dn: DeliveryNote, data: dict) -> DeliveryNote:
        for k, v in data.items():
            if hasattr(dn, k):
                setattr(dn, k, v)
        self.db.commit()
        self.db.refresh(dn)
        return dn

    def delete(self, dn: DeliveryNote) -> None:
        self.db.delete(dn)
        self.db.commit()
