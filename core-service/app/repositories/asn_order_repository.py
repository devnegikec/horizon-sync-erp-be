"""ASN Order repository"""

from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.asn_order import AsnOrder, AsnOrderItem
from app.models.item import Item


class AsnOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> AsnOrder:
        asn_order = AsnOrder(**data)
        self.db.add(asn_order)
        self.db.commit()
        self.db.refresh(asn_order)
        return asn_order

    def get_by_id(self, asn_order_id: UUID, organization_id: UUID) -> AsnOrder | None:
        return (
            self.db.query(AsnOrder)
            .filter(
                AsnOrder.id == asn_order_id,
                AsnOrder.organization_id == organization_id,
            )
            .first()
        )

    def get_by_id_with_items(
        self, asn_order_id: UUID, organization_id: UUID
    ) -> AsnOrder | None:
        return (
            self.db.query(AsnOrder)
            .options(
                joinedload(AsnOrder.from_warehouse),
                joinedload(AsnOrder.to_warehouse),
                joinedload(AsnOrder.items).joinedload(AsnOrderItem.item),
            )
            .filter(
                AsnOrder.id == asn_order_id,
                AsnOrder.organization_id == organization_id,
            )
            .first()
        )

    def list_asn_orders(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        sort_by: str = "order_date",
        sort_order: str = "desc",
    ) -> tuple[list[AsnOrder], int]:
        q = (
            self.db.query(AsnOrder)
            .options(
                joinedload(AsnOrder.from_warehouse),
                joinedload(AsnOrder.to_warehouse),
            )
            .filter(AsnOrder.organization_id == organization_id)
        )
        if status is not None:
            q = q.filter(AsnOrder.status == status)
        total = q.count()
        col = getattr(AsnOrder, sort_by, AsnOrder.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, asn_order: AsnOrder, data: dict) -> AsnOrder:
        for k, v in data.items():
            if hasattr(asn_order, k):
                setattr(asn_order, k, v)
        self.db.commit()
        self.db.refresh(asn_order)
        return asn_order

    def delete(self, asn_order: AsnOrder) -> None:
        self.db.delete(asn_order)
        self.db.commit()

    def update_item_delivered_qty(self, item_id: UUID, qty_to_add) -> None:
        item = (
            self.db.query(AsnOrderItem).filter(AsnOrderItem.id == item_id).first()
        )
        if item:
            item.delivered_qty += qty_to_add
            self.db.commit()
