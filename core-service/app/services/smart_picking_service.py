"""Smart Picking service — allocation suggestions, pick list creation with stock
reservation, and delivery note creation with stock deduction + audit trail."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ResourceNotFoundException,
    StateError,
    ValidationError,
)
from app.models.base import (
    DocumentStatus,
    MovementType,
    PickListStatus,
    SalesOrderStatus,
)
from app.models.delivery_note import DeliveryNote, DeliveryNoteItem
from app.models.item import Item
from app.models.pick_list import PickList, PickListItem
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.stock_level import StockLevel
from app.models.stock_movement import StockMovement
from app.models.warehouse import Warehouse


class SmartPickingService:
    def __init__(self, db: Session):
        self.db = db

    # ── 1. Suggest Allocation ───────────────────────────────────────

    def suggest_allocation(self, sales_order_id: UUID, organization_id: UUID) -> dict:
        """Suggest warehouse allocation for every SO line item.

        For each item, stock_levels rows are ordered by quantity_available DESC
        so the richest warehouse is consumed first.  If one warehouse can't
        satisfy the full qty, the remainder spills to the next warehouse.
        """
        so = (
            self.db.query(SalesOrder)
            .filter(
                SalesOrder.id == sales_order_id,
                SalesOrder.organization_id == organization_id,
            )
            .first()
        )
        if not so:
            raise ResourceNotFoundException(f"Sales order {sales_order_id} not found")

        allowed = {SalesOrderStatus.CONFIRMED, SalesOrderStatus.PARTIALLY_DELIVERED}
        if so.status not in allowed:
            raise StateError(
                f"Sales order must be in confirmed or partially_delivered status, "
                f"currently '{so.status.value}'",
                current_state=so.status.value,
                required_state=[s.value for s in allowed],
            )

        suggestions: list[dict] = []
        unallocated: list[dict] = []

        for so_item in so.items:
            remaining = so_item.qty - (so_item.delivered_qty or 0)
            if remaining <= 0:
                continue

            item = self.db.query(Item).filter(Item.id == so_item.item_id).first()
            if not item:
                continue

            # Fetch stock levels ordered by availability (richest first)
            stock_rows = (
                self.db.query(StockLevel)
                .filter(
                    StockLevel.product_id == so_item.item_id,
                    StockLevel.organization_id == organization_id,
                    StockLevel.quantity_available > 0,
                )
                .order_by(StockLevel.quantity_available.desc())
                .all()
            )

            still_needed = remaining
            for sl in stock_rows:
                if still_needed <= 0:
                    break
                wh = (
                    self.db.query(Warehouse)
                    .filter(Warehouse.id == sl.warehouse_id)
                    .first()
                )
                alloc_qty = min(Decimal(str(sl.quantity_available)), still_needed)
                suggestions.append(
                    {
                        "item_id": so_item.item_id,
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "warehouse_id": sl.warehouse_id,
                        "warehouse_code": wh.code if wh else "",
                        "warehouse_name": wh.name if wh else "",
                        "suggested_qty": alloc_qty,
                        "current_available": sl.quantity_available,
                        "uom": so_item.uom,
                    }
                )
                still_needed -= alloc_qty

            if still_needed > 0:
                unallocated.append(
                    {
                        "item_id": str(so_item.item_id),
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "short_qty": float(still_needed),
                        "uom": so_item.uom,
                    }
                )

        return {
            "sales_order_id": so.id,
            "sales_order_no": so.sales_order_no,
            "customer_id": so.customer_id,
            "suggestions": suggestions,
            "unallocated": unallocated,
        }

    # ── 2. Create Pick List & Reserve Stock ─────────────────────────

    def create_pick_list(
        self,
        sales_order_id: UUID,
        allocations: list[dict],
        organization_id: UUID,
        user_id: UUID,
        remarks: str | None = None,
    ) -> dict:
        """Create a pick list from confirmed allocations and reserve stock.

        Within a single transaction:
        1. Validate the sales order status
        2. Create pick_list + pick_list_items
        3. For each allocation, UPDATE stock_levels:
           quantity_reserved += qty, quantity_available -= qty
        """
        so = (
            self.db.query(SalesOrder)
            .filter(
                SalesOrder.id == sales_order_id,
                SalesOrder.organization_id == organization_id,
            )
            .first()
        )
        if not so:
            raise ResourceNotFoundException(f"Sales order {sales_order_id} not found")

        allowed = {SalesOrderStatus.CONFIRMED, SalesOrderStatus.PARTIALLY_DELIVERED}
        if so.status not in allowed:
            raise StateError(
                f"Sales order must be confirmed or partially_delivered, "
                f"currently '{so.status.value}'",
                current_state=so.status.value,
                required_state=[s.value for s in allowed],
            )

        # Validate every allocation has sufficient available stock
        for alloc in allocations:
            sl = (
                self.db.query(StockLevel)
                .filter(
                    StockLevel.product_id == alloc["item_id"],
                    StockLevel.warehouse_id == alloc["warehouse_id"],
                    StockLevel.organization_id == organization_id,
                )
                .with_for_update()  # row-level lock
                .first()
            )
            if not sl:
                raise ValidationError(
                    f"No stock level found for item {alloc['item_id']} "
                    f"in warehouse {alloc['warehouse_id']}"
                )
            if sl.quantity_available < int(alloc["qty"]):
                raise ValidationError(
                    f"Insufficient stock for item {alloc['item_id']} in warehouse "
                    f"{alloc['warehouse_id']}: available={sl.quantity_available}, "
                    f"requested={alloc['qty']}"
                )

        # Use the first allocation's warehouse as the pick list header warehouse
        primary_warehouse_id = allocations[0]["warehouse_id"]

        # Generate pick list number
        now = datetime.now(UTC)
        count = (
            self.db.query(func.count(PickList.id))
            .filter(PickList.organization_id == organization_id)
            .scalar()
            or 0
        )
        pick_list_no = f"PL-{now.strftime('%Y')}-{count + 1:04d}"

        pick_list = PickList(
            id=uuid.uuid4(),
            organization_id=organization_id,
            pick_list_no=pick_list_no,
            warehouse_id=primary_warehouse_id,
            status=PickListStatus.DRAFT,
            pick_date=now,
            reference_type="sales_order",
            reference_id=so.id,
            remarks=remarks,
            created_by=user_id,
            updated_by=user_id,
        )
        self.db.add(pick_list)
        self.db.flush()

        pick_items = []
        for idx, alloc in enumerate(allocations):
            pli = PickListItem(
                id=uuid.uuid4(),
                organization_id=organization_id,
                pick_list_id=pick_list.id,
                item_id=alloc["item_id"],
                warehouse_id=alloc["warehouse_id"],
                qty=alloc["qty"],
                picked_qty=0,
                uom=alloc["uom"],
                sort_order=idx,
            )
            self.db.add(pli)
            pick_items.append(pli)

            # Reserve stock
            sl = (
                self.db.query(StockLevel)
                .filter(
                    StockLevel.product_id == alloc["item_id"],
                    StockLevel.warehouse_id == alloc["warehouse_id"],
                    StockLevel.organization_id == organization_id,
                )
                .with_for_update()
                .first()
            )
            qty_int = int(alloc["qty"])
            sl.quantity_reserved = (sl.quantity_reserved or 0) + qty_int
            sl.quantity_available = (sl.quantity_available or 0) - qty_int

        self.db.commit()
        self.db.refresh(pick_list)

        return {
            "id": pick_list.id,
            "pick_list_no": pick_list.pick_list_no,
            "status": pick_list.status.value,
            "sales_order_id": so.id,
            "sales_order_no": so.sales_order_no,
            "items": [
                {
                    "id": pi.id,
                    "item_id": pi.item_id,
                    "warehouse_id": pi.warehouse_id,
                    "qty": pi.qty,
                    "picked_qty": pi.picked_qty,
                    "uom": pi.uom,
                }
                for pi in pick_items
            ],
            "created_at": pick_list.created_at,
        }

    # ── 3. Create Delivery Note from Pick List ──────────────────────

    def create_delivery_from_pick_list(
        self,
        pick_list_id: UUID,
        organization_id: UUID,
        user_id: UUID,
        delivery_date: datetime | None = None,
        remarks: str | None = None,
    ) -> dict:
        """Convert a pick list into a delivery note.

        Within a single transaction:
        1. Validate pick list exists and is in draft/in_progress status
        2. Resolve the sales order to get customer_id
        3. Create delivery_note + delivery_note_items
        4. UPDATE stock_levels: decrement quantity_on_hand and quantity_reserved
        5. INSERT stock_movements for audit trail
        6. Mark pick list as completed
        """
        pl = (
            self.db.query(PickList)
            .filter(
                PickList.id == pick_list_id,
                PickList.organization_id == organization_id,
            )
            .first()
        )
        if not pl:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")

        allowed = {PickListStatus.DRAFT, PickListStatus.IN_PROGRESS}
        if pl.status not in allowed:
            raise StateError(
                f"Pick list must be draft or in_progress, currently '{pl.status.value}'",
                current_state=pl.status.value,
                required_state=[s.value for s in allowed],
            )

        if pl.reference_type != "sales_order" or not pl.reference_id:
            raise ValidationError(
                "Pick list must reference a sales_order to create a delivery note"
            )

        so = (
            self.db.query(SalesOrder)
            .filter(
                SalesOrder.id == pl.reference_id,
                SalesOrder.organization_id == organization_id,
            )
            .first()
        )
        if not so:
            raise ResourceNotFoundException(
                f"Referenced sales order {pl.reference_id} not found"
            )

        _ = pl.items  # eager load

        now = datetime.now(UTC)
        dn_delivery_date = delivery_date or now

        # Generate delivery note number
        dn_count = (
            self.db.query(func.count(DeliveryNote.id))
            .filter(DeliveryNote.organization_id == organization_id)
            .scalar()
            or 0
        )
        dn_no = f"DN-{now.strftime('%Y')}-{dn_count + 1:04d}"

        dn = DeliveryNote(
            id=uuid.uuid4(),
            organization_id=organization_id,
            delivery_note_no=dn_no,
            customer_id=so.customer_id,
            delivery_date=dn_delivery_date,
            status=DocumentStatus.SUBMITTED,
            warehouse_id=pl.warehouse_id,
            pick_list_id=pl.id,
            reference_type="sales_order",
            reference_id=so.id,
            remarks=remarks,
            submitted_at=now,
            created_by=user_id,
            updated_by=user_id,
        )
        self.db.add(dn)
        self.db.flush()

        dn_items = []
        movements_created = 0

        # Build a map of SO item rates for pricing on DN items
        so_item_rates: dict[UUID, tuple[Decimal, Decimal]] = {}
        for soi in so.items:
            so_item_rates[soi.item_id] = (soi.rate, soi.amount)

        for pli in pl.items:
            rate = so_item_rates.get(pli.item_id, (Decimal("0"), Decimal("0")))[0]
            amount = Decimal(str(pli.qty)) * rate

            dni = DeliveryNoteItem(
                id=uuid.uuid4(),
                organization_id=organization_id,
                delivery_note_id=dn.id,
                item_id=pli.item_id,
                qty=pli.qty,
                uom=pli.uom,
                rate=rate,
                amount=amount,
                warehouse_id=pli.warehouse_id,
                sort_order=pli.sort_order,
            )
            self.db.add(dni)
            dn_items.append(dni)

            qty_int = int(pli.qty)

            # Update stock levels — decrement on_hand and reserved
            sl = (
                self.db.query(StockLevel)
                .filter(
                    StockLevel.product_id == pli.item_id,
                    StockLevel.warehouse_id == pli.warehouse_id,
                    StockLevel.organization_id == organization_id,
                )
                .with_for_update()
                .first()
            )
            if sl:
                sl.quantity_on_hand = (sl.quantity_on_hand or 0) - qty_int
                sl.quantity_reserved = (sl.quantity_reserved or 0) - qty_int
                # quantity_available stays the same (on_hand-reserved both drop)

            # Audit trail — stock movement
            sm = StockMovement(
                id=uuid.uuid4(),
                organization_id=organization_id,
                product_id=pli.item_id,
                warehouse_id=pli.warehouse_id,
                movement_type=MovementType.OUT,
                quantity=qty_int,
                unit_cost=rate,
                reference_type="delivery_note",
                reference_id=dn.id,
                notes=f"Delivery from pick list {pl.pick_list_no}",
                performed_by=user_id,
                performed_at=now,
            )
            self.db.add(sm)
            movements_created += 1

        # Mark pick list as completed
        pl.status = PickListStatus.COMPLETED
        pl.completed_at = now
        pl.updated_by = user_id

        # Update delivered_qty on sales order items
        for pli in pl.items:
            soi = (
                self.db.query(SalesOrderItem)
                .filter(
                    SalesOrderItem.sales_order_id == so.id,
                    SalesOrderItem.item_id == pli.item_id,
                )
                .first()
            )
            if soi:
                soi.delivered_qty = (soi.delivered_qty or 0) + pli.qty

        # Update SO status based on delivery completeness
        self.db.refresh(so)
        all_delivered = all(soi.delivered_qty >= soi.qty for soi in so.items)
        if all_delivered:
            so.status = SalesOrderStatus.DELIVERED
        else:
            so.status = SalesOrderStatus.PARTIALLY_DELIVERED

        self.db.commit()
        self.db.refresh(dn)

        return {
            "id": dn.id,
            "delivery_note_no": dn.delivery_note_no,
            "customer_id": dn.customer_id,
            "status": dn.status.value,
            "pick_list_id": pl.id,
            "items": [
                {
                    "id": di.id,
                    "item_id": di.item_id,
                    "warehouse_id": di.warehouse_id,
                    "qty": di.qty,
                    "uom": di.uom,
                    "rate": di.rate,
                    "amount": di.amount,
                }
                for di in dn_items
            ],
            "stock_movements_created": movements_created,
            "created_at": dn.created_at,
        }
