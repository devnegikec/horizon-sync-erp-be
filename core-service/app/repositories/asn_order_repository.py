"""ASN Order repository"""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.asn_order import AsnOrder, AsnOrderItem


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
        warehouse_id: UUID | None = None,
        search: str | None = None,
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
        if warehouse_id is not None:
            q = q.filter(
                or_(
                    AsnOrder.warehouse_id_from == warehouse_id,
                    AsnOrder.warehouse_id_to == warehouse_id,
                )
            )
        if search:
            t = f"%{search}%"
            q = q.filter(AsnOrder.asn_order_no.ilike(t))
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
        item = self.db.query(AsnOrderItem).filter(AsnOrderItem.id == item_id).first()
        if item:
            item.delivered_qty += qty_to_add
            self.db.commit()

    def get_receiving_summary(self, asn_order_id: UUID) -> list[dict]:
        """Get aggregated receiving data per ASN line item across all linked slips.

        Returns list of dicts with keys:
            asn_item_id, item_id, sku, item_name, expected_qty,
            accepted_qty, rejected_qty, pending_qty
        """
        from sqlalchemy import func

        from app.models.receiving_slip import ReceivingSlip, ReceivingSlipItem

        # Get ASN items
        asn_items = (
            self.db.query(AsnOrderItem)
            .filter(AsnOrderItem.asn_order_id == asn_order_id)
            .all()
        )

        if not asn_items:
            return []

        # Get all receiving slips linked to this ASN
        slip_ids = (
            self.db.query(ReceivingSlip.id)
            .filter(ReceivingSlip.asn_order_id == asn_order_id)
            .subquery()
        )

        # Aggregate receiving data grouped by SKU (since ReceivingSlipItem uses SKU not item_id)
        receiving_agg = {}
        rows = (
            self.db.query(
                ReceivingSlipItem.sku,
                ReceivingSlipItem.flag,
                func.sum(ReceivingSlipItem.quantity).label("total_qty"),
            )
            .filter(ReceivingSlipItem.slip_id.in_(slip_ids))
            .group_by(ReceivingSlipItem.sku, ReceivingSlipItem.flag)
            .all()
        )
        for sku, flag, qty in rows:
            if sku not in receiving_agg:
                receiving_agg[sku] = {"accepted": 0, "rejected": 0}
            if flag == "rejected":
                receiving_agg[sku]["rejected"] += int(qty) if qty else 0
            else:
                # ok, short, damaged all count as "accepted" (physically present)
                receiving_agg[sku]["accepted"] += int(qty) if qty else 0

        result = []
        for asn_item in asn_items:
            sku = asn_item.item.sku if asn_item.item else None
            agg = receiving_agg.get(sku, {"accepted": 0, "rejected": 0})
            accepted = agg["accepted"]
            rejected = agg["rejected"]
            expected = int(asn_item.qty) if asn_item.qty else 0
            pending = expected - accepted - rejected

            result.append(
                {
                    "asn_item_id": str(asn_item.id),
                    "item_id": str(asn_item.item_id),
                    "sku": sku,
                    "item_name": asn_item.item.name if asn_item.item else None,
                    "expected_qty": expected,
                    "accepted_qty": accepted,
                    "rejected_qty": rejected,
                    "pending_qty": max(0, pending),
                    "over_qty": abs(pending) if pending < 0 else 0,
                }
            )

        return result
