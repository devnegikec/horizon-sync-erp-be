"""Purchase Order repository"""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine


class PurchaseOrderRepository:
    """Repository for Purchase Order operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> PurchaseOrder:
        """Create a new Purchase Order"""
        po = PurchaseOrder(**data)
        self.db.add(po)
        self.db.commit()
        self.db.refresh(po)
        return po

    def get_by_id(self, po_id: UUID, organization_id: UUID, for_update: bool = False) -> PurchaseOrder | None:
        """
        Get Purchase Order by ID with all relationships.

        Args:
            po_id: Purchase Order ID
            organization_id: Organization ID
            for_update: If True, use SELECT FOR UPDATE to lock the row for concurrent updates

        Returns:
            PurchaseOrder or None
        """
        query = (
            self.db.query(PurchaseOrder)
            .options(joinedload(PurchaseOrder.line_items))
            .filter(
                PurchaseOrder.id == po_id,
                PurchaseOrder.organization_id == organization_id,
                PurchaseOrder.deleted_at.is_(None),
            )
        )

        if for_update:
            query = query.with_for_update()

        return query.first()

    def list_purchase_orders(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        rfq_id: UUID | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: str | None = None,
    ) -> tuple[list[PurchaseOrder], int]:
        """List Purchase Orders with pagination"""
        q = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.organization_id == organization_id,
            PurchaseOrder.deleted_at.is_(None),
        )

        if status is not None:
            q = q.filter(PurchaseOrder.status == status)

        if rfq_id is not None:
            q = q.filter(PurchaseOrder.rfq_id == rfq_id)

        total = q.count()

        col = getattr(PurchaseOrder, sort_by, PurchaseOrder.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())

        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, po: PurchaseOrder, data: dict) -> PurchaseOrder:
        """Update Purchase Order"""
        for k, v in data.items():
            if hasattr(po, k):
                setattr(po, k, v)
        self.db.commit()
        self.db.refresh(po)
        return po

    def delete(self, po: PurchaseOrder) -> None:
        """Delete Purchase Order"""
        self.db.delete(po)
        self.db.commit()

    def create_line_item(self, data: dict) -> PurchaseOrderLine:
        """Create a Purchase Order line item"""
        line_item = PurchaseOrderLine(**data)
        self.db.add(line_item)
        self.db.commit()
        self.db.refresh(line_item)
        return line_item

    def delete_line_items(self, po_id: UUID) -> None:
        """Delete all line items for a Purchase Order"""
        self.db.query(PurchaseOrderLine).filter(
            PurchaseOrderLine.purchase_order_id == po_id
        ).delete()
        self.db.commit()

    def get_line_items_count(self, po_id: UUID) -> int:
        """Get count of line items for a Purchase Order"""
        return (
            self.db.query(func.count(PurchaseOrderLine.id))
            .filter(PurchaseOrderLine.purchase_order_id == po_id)
            .scalar()
        )

    def update_line_item_received_quantity(
        self, line_id: UUID, received_quantity
    ) -> PurchaseOrderLine:
        """Update received quantity for a Purchase Order line item"""
        line = self.db.query(PurchaseOrderLine).filter(
            PurchaseOrderLine.id == line_id
        ).first()
        if line:
            line.received_quantity = received_quantity
            self.db.commit()
            self.db.refresh(line)
        return line
