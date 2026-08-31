"""ASN Order repository"""

from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.asn_order import AsnOrder, AsnOrderItem
from app.models.vehicle import VehicleArrival


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
                selectinload(AsnOrder.vehicle_arrivals).joinedload(
                    VehicleArrival.vehicle
                ),
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
        source_warehouse_id: UUID | None = None,
        delivery_date_from=None,
        delivery_date_to=None,
        vehicle_no: str | None = None,
        search: str | None = None,
        asn_type: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[AsnOrder], int]:
        q = (
            self.db.query(AsnOrder)
            .options(
                joinedload(AsnOrder.from_warehouse),
                joinedload(AsnOrder.to_warehouse),
                selectinload(AsnOrder.vehicle_arrivals).joinedload(
                    VehicleArrival.vehicle
                ),
            )
            .filter(AsnOrder.organization_id == organization_id)
        )
        if status is not None:
            q = q.filter(AsnOrder.status == status)
        if warehouse_id is not None:
            # A selected warehouse sees its inbound ASNs (target) AND its
            # outgoing internal transfers (source). Both warehouses in an
            # internal transfer are owned by the organization, so the source
            # side also needs visibility of the transfer it is fulfilling.
            q = q.filter(
                or_(
                    AsnOrder.warehouse_id_to == warehouse_id,
                    and_(
                        AsnOrder.asn_type == "internal_transfer",
                        AsnOrder.warehouse_id_from == warehouse_id,
                    ),
                )
            )
        if source_warehouse_id is not None:
            q = q.filter(AsnOrder.warehouse_id_from == source_warehouse_id)
        if asn_type is not None:
            q = q.filter(AsnOrder.asn_type == asn_type)
        if delivery_date_from is not None:
            q = q.filter(AsnOrder.delivery_date >= delivery_date_from)
        if delivery_date_to is not None:
            q = q.filter(AsnOrder.delivery_date <= delivery_date_to)
        if vehicle_no:
            from app.models.vehicle import (
                Vehicle,
                vehicle_arrival_asns,
            )

            q = (
                q.join(
                    vehicle_arrival_asns,
                    vehicle_arrival_asns.c.asn_order_id == AsnOrder.id,
                )
                .join(
                    VehicleArrival,
                    VehicleArrival.id == vehicle_arrival_asns.c.vehicle_arrival_id,
                )
                .join(Vehicle, Vehicle.id == VehicleArrival.vehicle_id)
                .filter(Vehicle.vehicle_no.ilike(f"%{vehicle_no}%"))
                .distinct()
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

        Returns finalized receipt quantities, grouped by ASN line item and
        classification. Active session scans are added by the endpoint so the
        same summary can be used during an in-progress receipt.
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
                receiving_agg[sku] = {
                    "accepted": 0,
                    "rejected": 0,
                    "short": 0,
                    "excess": 0,
                    "damaged": 0,
                    "hold": 0,
                }

            quantity = int(qty) if qty else 0
            category = {
                "rejected": "rejected",
                "short": "short",
                "excess": "excess",
                "damaged": "damaged",
                "hold": "hold",
                "quarantine": "hold",
            }.get(flag or "", "accepted")
            receiving_agg[sku][category] += quantity

        # Group ASN lines by SKU so aggregated receipt quantities can be
        # distributed across duplicate-SKU lines instead of being duplicated.
        category_keys = ("accepted", "rejected", "short", "excess", "damaged", "hold")
        line_rows: list[dict] = []
        sku_line_indices: dict[str, list[int]] = {}
        for asn_item in asn_items:
            sku = asn_item.item.sku if asn_item.item else None
            expected = int(asn_item.qty) if asn_item.qty else 0
            idx = len(line_rows)
            line_rows.append(
                {
                    "asn_item_id": str(asn_item.id),
                    "item_id": str(asn_item.item_id),
                    "sku": sku,
                    "item_name": asn_item.item.item_name if asn_item.item else None,
                    "expected_qty": expected,
                    "allocated": dict.fromkeys(category_keys, 0),
                }
            )
            if sku:
                sku_line_indices.setdefault(sku, []).append(idx)

        for sku, totals in receiving_agg.items():
            indices = sku_line_indices.get(sku)
            if not indices:
                continue
            for category in category_keys:
                remaining = totals.get(category, 0)
                if remaining <= 0:
                    continue
                # Fill each duplicate line up to its expected quantity, then
                # attach any surplus to the last line (single overage).
                for idx in indices:
                    if remaining <= 0:
                        break
                    allocated = sum(line_rows[idx]["allocated"].values())
                    outstanding = max(0, line_rows[idx]["expected_qty"] - allocated)
                    take = min(outstanding, remaining)
                    line_rows[idx]["allocated"][category] += take
                    remaining -= take
                if remaining > 0:
                    line_rows[indices[-1]]["allocated"][category] += remaining

        result = []
        for row in line_rows:
            agg = row["allocated"]
            accepted = agg["accepted"]
            rejected = agg["rejected"]
            short = agg["short"]
            excess = agg["excess"]
            damaged = agg["damaged"]
            hold = agg["hold"]
            expected = row["expected_qty"]
            resolved = accepted + rejected + excess + damaged + hold
            pending = expected - resolved

            result.append(
                {
                    "asn_item_id": row["asn_item_id"],
                    "item_id": row["item_id"],
                    "sku": row["sku"],
                    "item_name": row["item_name"],
                    "expected_qty": expected,
                    "accepted_qty": accepted,
                    "rejected_qty": rejected,
                    "short_qty": short,
                    "excess_qty": excess,
                    "damaged_qty": damaged,
                    "hold_qty": hold,
                    "pending_qty": max(0, pending),
                    "over_qty": abs(pending) if pending < 0 else 0,
                }
            )

        return result
