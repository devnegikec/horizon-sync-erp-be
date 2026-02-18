"""Sales Order repository"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.item import Item
from app.models.sales_order import SalesOrder, SalesOrderItem


class SalesOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> SalesOrder:
        sales_order = SalesOrder(**data)
        self.db.add(sales_order)
        self.db.commit()
        self.db.refresh(sales_order)
        return sales_order

    def get_by_id(
        self, sales_order_id: UUID, organization_id: UUID
    ) -> SalesOrder | None:
        return (
            self.db.query(SalesOrder)
            .filter(
                SalesOrder.id == sales_order_id,
                SalesOrder.organization_id == organization_id,
            )
            .first()
        )

    def get_by_id_with_items(
        self, sales_order_id: UUID, organization_id: UUID
    ) -> SalesOrder | None:
        return (
            self.db.query(SalesOrder)
            .options(
                joinedload(SalesOrder.items)
                .joinedload(SalesOrderItem.item)
                .joinedload(Item.item_group)
            )
            .filter(
                SalesOrder.id == sales_order_id,
                SalesOrder.organization_id == organization_id,
            )
            .first()
        )

    def list_sales_orders(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        customer_id: UUID | None = None,
        status: str | None = None,
        sort_by: str = "order_date",
        sort_order: str = "desc",
    ) -> tuple[list[SalesOrder], int]:
        q = self.db.query(SalesOrder).filter(
            SalesOrder.organization_id == organization_id
        )
        if customer_id is not None:
            q = q.filter(SalesOrder.customer_id == customer_id)
        if status is not None:
            q = q.filter(SalesOrder.status == status)
        total = q.count()
        col = getattr(SalesOrder, sort_by, SalesOrder.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, sales_order: SalesOrder, data: dict) -> SalesOrder:
        for k, v in data.items():
            if hasattr(sales_order, k):
                setattr(sales_order, k, v)
        self.db.commit()
        self.db.refresh(sales_order)
        return sales_order

    def delete(self, sales_order: SalesOrder) -> None:
        self.db.delete(sales_order)
        self.db.commit()

    def update_item_billed_qty(self, item_id: UUID, qty_to_add: Decimal) -> None:
        item = (
            self.db.query(SalesOrderItem).filter(SalesOrderItem.id == item_id).first()
        )
        if item:
            item.billed_qty += qty_to_add
            self.db.commit()

    def update_item_delivered_qty(self, item_id: UUID, qty_to_add: Decimal) -> None:
        item = (
            self.db.query(SalesOrderItem).filter(SalesOrderItem.id == item_id).first()
        )
        if item:
            item.delivered_qty += qty_to_add
            self.db.commit()
