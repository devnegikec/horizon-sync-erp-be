"""Outbound order service.

Manages the upstream outbound order lifecycle (ASN/SAP orders imported from
files) and converts a confirmed order into one or more pick lists.

An order carries its own line items plus a per-line ``stock_status`` flag
(``in_stock`` / ``out_of_stock``) derived from the warehouse ``stock_levels``
``quantity_available``, so a manager can see at a glance whether an order can
be fulfilled before confirming it.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationError
from app.models.base import (
    OutboundOrderItemStockStatus,
    OutboundOrderStatus,
    OutboundOrderType,
    PickListStatus,
)
from app.models.outbound_order import OutboundOrder, OutboundOrderItem
from app.models.pick_list import PickList, PickListItem
from app.models.stock_level import StockLevel


class OutboundOrderService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # STOCK STATUS
    # ------------------------------------------------------------------

    def refresh_stock_status(self, order: OutboundOrder, commit: bool = True) -> OutboundOrder:
        """Recompute each order line's fulfilment availability from stock_levels."""
        item_ids = [item.item_id for item in order.items]
        if not item_ids:
            return order

        levels = (
            self.db.query(StockLevel)
            .filter(
                StockLevel.organization_id == order.organization_id,
                StockLevel.warehouse_id == order.warehouse_id,
                StockLevel.product_id.in_(item_ids),
            )
            .all()
        )
        available_by_item = {level.product_id: level for level in levels}

        for item in order.items:
            level = available_by_item.get(item.item_id)
            available = Decimal(str(level.quantity_available or 0)) if level else Decimal("0")
            item.available_qty = available
            item.stock_status = (
                OutboundOrderItemStockStatus.IN_STOCK
                if available >= Decimal(str(item.qty))
                else OutboundOrderItemStockStatus.OUT_OF_STOCK
            )

        if commit:
            self.db.commit()
            self.db.refresh(order)
        return order

    # ------------------------------------------------------------------
    # QUERIES
    # ------------------------------------------------------------------

    def list_orders(
        self,
        org_id: UUID,
        warehouse_id: UUID | None = None,
        status: str | None = None,
        order_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[OutboundOrder], dict]:
        query = self.db.query(OutboundOrder).filter(
            OutboundOrder.organization_id == org_id
        )
        if warehouse_id:
            query = query.filter(OutboundOrder.warehouse_id == warehouse_id)
        if status:
            query = query.filter(OutboundOrder.status == OutboundOrderStatus(status))
        if order_type:
            query = query.filter(OutboundOrder.order_type == OutboundOrderType(order_type))

        total = query.count()
        orders = (
            query.order_by(OutboundOrder.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        total_pages = (total + page_size - 1) // page_size if page_size else 0
        pagination = {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return orders, pagination

    def get_status_counts(
        self,
        org_id: UUID,
        warehouse_id: UUID | None = None,
        order_type: str | None = None,
    ) -> dict:
        """Return per-status counts for outbound orders (unfiltered by status)."""
        query = (
            self.db.query(OutboundOrder.status, func.count(OutboundOrder.id))
            .filter(OutboundOrder.organization_id == org_id)
        )
        if warehouse_id:
            query = query.filter(OutboundOrder.warehouse_id == warehouse_id)
        if order_type:
            query = query.filter(OutboundOrder.order_type == OutboundOrderType(order_type))
        rows = query.group_by(OutboundOrder.status).all()
        counts = {
            (row[0].value if hasattr(row[0], "value") else row[0]): row[1]
            for row in rows
        }
        return {
            "total": sum(counts.values()),
            "draft": counts.get("draft", 0),
            "confirmed": counts.get("confirmed", 0),
            "pending_picking": counts.get("pending_picking", 0),
            "completed": counts.get("completed", 0),
            "cancelled": counts.get("cancelled", 0),
        }

    def get_order(self, order_id: UUID, org_id: UUID) -> OutboundOrder:
        order = (
            self.db.query(OutboundOrder)
            .filter(
                OutboundOrder.id == order_id,
                OutboundOrder.organization_id == org_id,
            )
            .first()
        )
        if order is None:
            raise ResourceNotFoundException(f"Outbound order {order_id} not found")
        return order

    # ------------------------------------------------------------------
    # MUTATIONS
    # ------------------------------------------------------------------

    def confirm_order(self, order_id: UUID, org_id: UUID) -> OutboundOrder:
        order = self.get_order(order_id, org_id)
        if order.status == OutboundOrderStatus.CANCELLED:
            raise ValidationError("Cannot confirm a cancelled order")
        if order.status in (
            OutboundOrderStatus.PENDING_PICKING,
            OutboundOrderStatus.COMPLETED,
        ):
            raise ValidationError(
                f"Order is already in '{order.status.value}' status"
            )
        order.status = OutboundOrderStatus.CONFIRMED
        self.db.commit()
        self.db.refresh(order)
        return self.refresh_stock_status(order)

    def create_order(
        self,
        org_id: UUID,
        warehouse_id: UUID,
        order_type: str,
        invoice_reference: str,
        items: list[dict],
        created_by: UUID | None = None,
    ) -> OutboundOrder:
        """Create a draft outbound order from a manual/invoice-style payload."""
        try:
            parsed_type = OutboundOrderType(order_type)
        except ValueError:
            raise ValidationError(
                f"Invalid order type '{order_type}' (expected 'sap' or 'asn')"
            )

        if not invoice_reference:
            raise ValidationError("Invoice reference is required")
        if not items:
            raise ValidationError("Order must contain at least one line item")

        from app.models.warehouse import Warehouse

        warehouse = (
            self.db.query(Warehouse)
            .filter(
                Warehouse.id == warehouse_id,
                Warehouse.organization_id == org_id,
            )
            .first()
        )
        if warehouse is None:
            raise ValidationError(
                f"Warehouse {warehouse_id} not found in organization"
            )

        from app.services.document_numbering_service import DocumentNumberingService

        order = OutboundOrder(
            organization_id=org_id,
            order_no=DocumentNumberingService(self.db).get_next_number(
                org_id, "outbound_order"
            ),
            order_type=parsed_type,
            warehouse_id=warehouse_id,
            status=OutboundOrderStatus.DRAFT,
            invoice_reference=invoice_reference,
            created_by=created_by,
        )
        self.db.add(order)
        self.db.flush()

        for line in items:
            self.db.add(
                OutboundOrderItem(
                    organization_id=org_id,
                    outbound_order_id=order.id,
                    item_id=line["item_id"],
                    warehouse_id=warehouse_id,
                    qty=line["quantity"],
                    uom=line.get("uom") or "pcs",
                    sku=line.get("sku"),
                    per_case_qty=line.get("per_case_qty"),
                    case_qty=line.get("case_qty"),
                    loose_qty=line.get("loose_qty"),
                    batch_no=line.get("batch_no"),
                )
            )

        self.db.commit()
        self.db.refresh(order)
        return self.refresh_stock_status(order)

    def create_pick_lists_from_order(
        self,
        order_id: UUID,
        org_id: UUID,
        worker_ids: list[UUID] | None = None,
        mode: str | None = None,
        exclude_out_of_stock: bool = True,
    ) -> list[PickList]:
        """Generate one or more pick lists from a confirmed order.

        When ``worker_ids`` is non-empty the order lines are split round-robin
        across the workers, producing one pick list per worker (mirroring the
        inbound put-away generation flow). An empty list creates a single
        unassigned pick list. Every generated pick list starts in
        ``pending_picking`` status and references the order.

        ``mode`` mirrors the put-away generation contract: ``auto`` (default)
        assigns bin locations via FIFO/FEFO resolution; ``manual`` leaves bin
        assignment to the worker.

        When ``exclude_out_of_stock`` is true (default), order lines with no
        available stock are skipped so the generated pick lists only carry
        fulfillable items (partial order).
        """
        order = self.get_order(order_id, org_id)

        if order.status != OutboundOrderStatus.CONFIRMED:
            raise ValidationError(
                f"Order must be confirmed before generating pick lists "
                f"(current status: '{order.status.value}')"
            )

        if not order.items:
            raise ValidationError("Order has no line items")

        # Recompute per-line availability so out-of-stock lines are excluded
        # from pick generation (partial order support).
        self.refresh_stock_status(order, commit=False)

        pickable_items = list(order.items)
        if exclude_out_of_stock:
            pickable_items = [
                item
                for item in order.items
                if Decimal(str(item.available_qty or 0)) > 0
            ]
            if not pickable_items:
                raise ValidationError(
                    "No items have available stock to pick; "
                    "nothing was generated for this order"
                )

        effective_mode = mode or "auto"
        if effective_mode not in {"auto", "manual"}:
            raise ValidationError(f"Invalid pick generation mode: {effective_mode}")

        workers = worker_ids or []
        for worker_id in workers:
            self._validate_worker(worker_id, order.warehouse_id, org_id)
        bucket_count = len(workers) if workers else 1

        from app.services.document_numbering_service import DocumentNumberingService

        numbering = DocumentNumberingService(self.db)

        # Split order items round-robin across buckets (worker count).
        buckets: list[list[OutboundOrderItem]] = [[] for _ in range(bucket_count)]
        for idx, item in enumerate(pickable_items):
            buckets[idx % bucket_count].append(item)

        pick_lists: list[PickList] = []
        for idx, bucket in enumerate(buckets):
            if not bucket:
                continue
            assigned_to = workers[idx] if workers else None
            pick_list = PickList(
                organization_id=org_id,
                pick_list_no=numbering.get_next_number(org_id, "pick_list"),
                warehouse_id=order.warehouse_id,
                status=PickListStatus.PENDING_PICKING,
                pick_date=datetime.now(UTC),
                reference_type="outbound_order",
                reference_id=order.id,
                invoice_reference=order.invoice_reference,
                assigned_to=assigned_to,
                invoice_data={
                    "order_no": order.order_no,
                    "order_type": order.order_type.value,
                    "order_id": str(order.id),
                },
            )
            self.db.add(pick_list)
            self.db.flush()

            for item in bucket:
                per_case, case_qty, loose_qty = self._resolve_packaging(
                    item.item_id,
                    org_id,
                    item.per_case_qty,
                    item.case_qty,
                    item.loose_qty,
                    item.qty,
                )

                # Split into master-pack-sized pick lines when a pack size is
                # known — one line per full master pack plus a loose remainder.
                pack_size = per_case
                if pack_size is not None and Decimal(str(pack_size)) > 1:
                    q = Decimal(str(item.qty))
                    pc = Decimal(str(pack_size))
                    split_lines = []
                    for _ in range(int(q // pc)):
                        split_lines.append((pc, pc, Decimal("1"), Decimal("0")))
                    remainder = q % pc
                    if remainder > 0:
                        split_lines.append((remainder, pc, Decimal("0"), remainder))
                else:
                    split_lines = [(item.qty, per_case, case_qty, loose_qty)]

                for line_qty, line_per_case, line_case, line_loose in split_lines:
                    self.db.add(
                        PickListItem(
                            organization_id=org_id,
                            pick_list_id=pick_list.id,
                            item_id=item.item_id,
                            warehouse_id=order.warehouse_id,
                            qty=line_qty,
                            picked_qty=Decimal("0"),
                            uom=item.uom,
                            per_case_qty=line_per_case,
                            case_qty=line_case,
                            loose_qty=line_loose,
                            batch_no=item.batch_no,
                            sort_order=0,
                        )
                    )
            pick_lists.append(pick_list)

        order.status = OutboundOrderStatus.PENDING_PICKING
        self.db.commit()

        # Resolve bin locations only in automatic mode. In manual mode the
        # worker assigns bins during picking.
        if effective_mode == "auto":
            from app.services.pick_list_service import PickListService

            pick_service = PickListService(self.db)
            for pick_list in pick_lists:
                pick_list = pick_service.resolve_bin_locations(pick_list.id, org_id)
                pick_service.reserve_pick_bins(pick_list, org_id)

        return pick_lists

    def _resolve_packaging(
        self,
        item_id: UUID,
        org_id: UUID,
        per_case_qty,
        case_qty,
        loose_qty,
        qty,
    ):
        """Derive the per-case/loose (master/child) breakdown for a pick line.

        When the imported order line omits ``per_case_qty`` (master pack size),
        fall back to the item's active packaging unit that defines
        ``items_per_master_pack`` (or ``conversion_factor``). ``case_qty`` and
        ``loose_qty`` are then computed from ``qty`` when missing so the picker
        surfaces the master/child split (requirement A2).
        """
        effective_per_case = per_case_qty
        if effective_per_case is None or Decimal(str(effective_per_case)) <= 0:
            from app.models.item_packaging_unit import ItemPackagingUnit

            master = (
                self.db.query(ItemPackagingUnit)
                .filter(
                    ItemPackagingUnit.item_id == item_id,
                    ItemPackagingUnit.organization_id == org_id,
                    ItemPackagingUnit.is_active.is_(True),
                    ItemPackagingUnit.is_base_unit.is_(False),
                )
                .order_by(ItemPackagingUnit.conversion_factor.asc())
                .first()
            )
            if master is not None:
                if master.items_per_master_pack is not None:
                    effective_per_case = Decimal(str(master.items_per_master_pack))
                elif master.conversion_factor is not None:
                    effective_per_case = Decimal(str(master.conversion_factor))

        effective_case = case_qty
        effective_loose = loose_qty
        if effective_per_case is not None and Decimal(str(effective_per_case)) > 0:
            q = Decimal(str(qty))
            pc = Decimal(str(effective_per_case))
            if effective_case is None:
                effective_case = q // pc
            if effective_loose is None:
                effective_loose = q % pc

        return effective_per_case, effective_case, effective_loose

    def _validate_worker(
        self, worker_id: UUID, warehouse_id: UUID, org_id: UUID
    ) -> None:
        """Reject workers that are inactive, cross-org, or not assigned to the
        order's warehouse before they are persisted on a pick list."""
        from app.models.warehouse_user import WarehouseUser

        assignment = (
            self.db.query(WarehouseUser)
            .filter(
                WarehouseUser.user_id == worker_id,
                WarehouseUser.organization_id == org_id,
                WarehouseUser.warehouse_id == warehouse_id,
                WarehouseUser.is_active == True,  # noqa: E712
            )
            .first()
        )
        if assignment is None:
            raise ValidationError(
                f"Worker '{worker_id}' is not an active member of this warehouse"
            )
