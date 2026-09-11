"""Packing slip service.

Groups picked goods from one or more completed outbound orders into a packing
slip (internal staging document). Each line traces back to its source pick
list and order, and carries the bin / handling unit it was staged on.

Lifecycle: draft → loading → dispatched (plus cancelled).
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationError
from app.models.base import OutboundOrderStatus, PackingSlipStatus, PickListStatus
from app.models.item import Item
from app.models.outbound_order import OutboundOrder
from app.models.packing_slip import PackingSlip, PackingSlipItem
from app.models.pick_list import PickList


class PackingSlipService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create_from_orders(
        self, order_ids: list[UUID], org_id: UUID, user_id: UUID
    ) -> PackingSlip:
        """Create a packing slip from one or more completed outbound orders.

        Gathers every picked pick-list line across the orders and stages it on
        a new packing slip. An order can only appear on one active (non-
        cancelled) packing slip to prevent double-packing.
        """
        from app.services.document_numbering_service import DocumentNumberingService

        unique_ids = list(dict.fromkeys(order_ids))
        orders = (
            self.db.query(OutboundOrder)
            .filter(
                OutboundOrder.id.in_(unique_ids),
                OutboundOrder.organization_id == org_id,
            )
            .with_for_update()
            .all()
        )
        if len(orders) != len(unique_ids):
            raise ResourceNotFoundException("One or more orders not found")

        warehouses = {o.warehouse_id for o in orders}
        if len(warehouses) != 1:
            raise ValidationError("All orders must belong to the same warehouse")

        for order in orders:
            if order.status != OutboundOrderStatus.COMPLETED:
                raise ValidationError(
                    f"Order '{order.order_no}' is not completed "
                    f"(current status: '{order.status.value}')"
                )

        # Lock the pick lists for these orders so order-based packing serializes
        # with pick-list-based packing (both target the same pick-list rows) and
        # cannot double-pack the same picked goods.
        pick_lists_by_order: dict[UUID, list[PickList]] = {}
        all_pick_lists = (
            self.db.query(PickList)
            .filter(
                PickList.organization_id == org_id,
                PickList.reference_type == "outbound_order",
                PickList.reference_id.in_(unique_ids),
            )
            .with_for_update()
            .all()
        )
        for pl in all_pick_lists:
            pick_lists_by_order.setdefault(pl.reference_id, []).append(pl)

        pick_list_ids = [pl.id for pl in all_pick_lists]
        if pick_list_ids:
            already = (
                self.db.query(PackingSlipItem)
                .join(PackingSlip, PackingSlip.id == PackingSlipItem.packing_slip_id)
                .filter(
                    PackingSlipItem.organization_id == org_id,
                    PackingSlipItem.pick_list_id.in_(pick_list_ids),
                    PackingSlip.status != PackingSlipStatus.CANCELLED,
                )
                .first()
            )
            if already is not None:
                raise ValidationError(
                    "One or more pick lists are already packed on an active packing slip"
                )

        numbering = DocumentNumberingService(self.db)
        slip = PackingSlip(
            organization_id=org_id,
            packing_slip_no=numbering.get_next_number(org_id, "packing_slip"),
            warehouse_id=warehouses.pop(),
            status=PackingSlipStatus.DRAFT,
            created_by=user_id,
            updated_by=user_id,
        )
        self.db.add(slip)
        self.db.flush()

        sort_order = 0
        for order in orders:
            for pl in pick_lists_by_order.get(order.id, []):
                for pli in pl.items:
                    picked = Decimal(str(pli.picked_qty or 0))
                    if picked <= 0:
                        continue
                    self.db.add(
                        PackingSlipItem(
                            organization_id=org_id,
                            packing_slip_id=slip.id,
                            order_id=order.id,
                            pick_list_id=pl.id,
                            item_id=pli.item_id,
                            qty=picked,
                            uom=pli.uom,
                            per_case_qty=pli.per_case_qty,
                            case_qty=pli.case_qty,
                            loose_qty=pli.loose_qty,
                            batch_no=pli.batch_no,
                            serial_nos=pli.serial_nos,
                            bin_location_id=pli.bin_location_id,
                            handling_unit_id=pli.handling_unit_id,
                            sort_order=sort_order,
                        )
                    )
                    sort_order += 1

        if sort_order == 0:
            raise ValidationError(
                "No picked items found to pack for the selected order(s)"
            )

        self.db.commit()
        self.db.refresh(slip)
        return slip

    def pack_pick_lists(
        self,
        pick_list_ids: list[UUID],
        org_id: UUID,
        user_id: UUID,
        packing_slip_id: UUID | None = None,
    ) -> PackingSlip:
        """Pack one or more completed pick lists into a packing slip.

        Creates a new draft packing slip when ``packing_slip_id`` is None, or
        appends the pick lists' picked items to the existing draft slip. Pick
        lists may come from different orders, so multiple orders can share one
        slip and an order can be spread across multiple slips.
        """
        from app.services.document_numbering_service import DocumentNumberingService

        unique_ids = list(dict.fromkeys(pick_list_ids))
        pick_lists = (
            self.db.query(PickList)
            .filter(
                PickList.id.in_(unique_ids),
                PickList.organization_id == org_id,
            )
            .with_for_update()
            .all()
        )
        if len(pick_lists) != len(unique_ids):
            raise ResourceNotFoundException("One or more pick lists not found")

        packable = {
            PickListStatus.PICK_COMPLETE,
            PickListStatus.COMPLETED,
            PickListStatus.READY_FOR_DISPATCH,
        }
        for pl in pick_lists:
            if pl.status not in packable:
                raise ValidationError(
                    f"Pick list '{pl.pick_list_no}' is not completed "
                    f"(current status: '{pl.status.value}')"
                )

        warehouses = {pl.warehouse_id for pl in pick_lists}
        if len(warehouses) != 1:
            raise ValidationError("All pick lists must belong to the same warehouse")
        warehouse_id = warehouses.pop()

        already = (
            self.db.query(PackingSlipItem)
            .join(PackingSlip, PackingSlip.id == PackingSlipItem.packing_slip_id)
            .filter(
                PackingSlipItem.organization_id == org_id,
                PackingSlipItem.pick_list_id.in_(unique_ids),
                PackingSlip.status != PackingSlipStatus.CANCELLED,
            )
            .first()
        )
        if already is not None:
            raise ValidationError(
                "One or more pick lists are already packed on an active packing slip"
            )

        if packing_slip_id is not None:
            slip = self._get(packing_slip_id, org_id, for_update=True)
            if slip.status != PackingSlipStatus.DRAFT:
                raise ValidationError("Can only add items to a draft packing slip")
            if slip.warehouse_id != warehouse_id:
                raise ValidationError("Packing slip belongs to a different warehouse")
        else:
            numbering = DocumentNumberingService(self.db)
            slip = PackingSlip(
                organization_id=org_id,
                packing_slip_no=numbering.get_next_number(org_id, "packing_slip"),
                warehouse_id=warehouse_id,
                status=PackingSlipStatus.DRAFT,
                created_by=user_id,
                updated_by=user_id,
            )
            self.db.add(slip)
            self.db.flush()

        sort_order = (
            max((i.sort_order or 0) for i in slip.items) + 1 if slip.items else 0
        )
        added = 0
        for pl in pick_lists:
            order_id = pl.reference_id if pl.reference_type == "outbound_order" else None
            for pli in pl.items:
                picked = Decimal(str(pli.picked_qty or 0))
                if picked <= 0:
                    continue
                self.db.add(
                    PackingSlipItem(
                        organization_id=org_id,
                        packing_slip_id=slip.id,
                        order_id=order_id,
                        pick_list_id=pl.id,
                        item_id=pli.item_id,
                        qty=picked,
                        uom=pli.uom,
                        per_case_qty=pli.per_case_qty,
                        case_qty=pli.case_qty,
                        loose_qty=pli.loose_qty,
                        batch_no=pli.batch_no,
                        serial_nos=pli.serial_nos,
                        bin_location_id=pli.bin_location_id,
                        handling_unit_id=pli.handling_unit_id,
                        sort_order=sort_order,
                    )
                )
                sort_order += 1
                added += 1

        if added == 0:
            raise ValidationError(
                "No picked items found to pack for the selected pick list(s)"
            )

        self.db.commit()
        self.db.refresh(slip)
        return slip

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get_packing_slip(self, slip_id: UUID, org_id: UUID) -> PackingSlip:
        return self._get(slip_id, org_id)

    def list_packing_slips(
        self,
        org_id: UUID,
        page: int = 1,
        page_size: int = 20,
        warehouse_id: UUID | None = None,
        status: str | None = None,
    ) -> tuple[list[dict], dict]:
        query = self.db.query(PackingSlip).filter(
            PackingSlip.organization_id == org_id
        )
        if warehouse_id is not None:
            query = query.filter(PackingSlip.warehouse_id == warehouse_id)
        if status:
            query = query.filter(PackingSlip.status == PackingSlipStatus(status))

        total = query.count()
        slips = (
            query.order_by(PackingSlip.created_at.desc())
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
        return [self._to_list_item(s) for s in slips], pagination

    def get_status_counts(
        self,
        org_id: UUID,
        warehouse_id: UUID | None = None,
    ) -> dict:
        """Return per-status counts for packing slips (unfiltered by status)."""
        query = (
            self.db.query(PackingSlip.status, func.count(PackingSlip.id))
            .filter(PackingSlip.organization_id == org_id)
        )
        if warehouse_id is not None:
            query = query.filter(PackingSlip.warehouse_id == warehouse_id)
        rows = query.group_by(PackingSlip.status).all()
        counts = {
            (row[0].value if hasattr(row[0], "value") else row[0]): row[1]
            for row in rows
        }
        return {
            "total": sum(counts.values()),
            "draft": counts.get("draft", 0),
            "loading": counts.get("loading", 0),
            "dispatched": counts.get("dispatched", 0),
            "cancelled": counts.get("cancelled", 0),
        }

    # ------------------------------------------------------------------
    # LIFECYCLE
    # ------------------------------------------------------------------

    def mark_loading(self, slip_id: UUID, org_id: UUID, user_id: UUID) -> PackingSlip:
        """Move a draft packing slip to ``loading``."""
        slip = self._get(slip_id, org_id)
        if slip.status != PackingSlipStatus.DRAFT:
            raise ValidationError(
                f"Cannot move packing slip from '{slip.status.value}' to loading"
            )
        slip.status = PackingSlipStatus.LOADING
        slip.updated_by = user_id
        self.db.commit()
        self.db.refresh(slip)
        return slip

    def dispatch(self, slip_id: UUID, org_id: UUID, user_id: UUID) -> dict:
        """Dispatch a loading packing slip (final reconciliation before gate-out).

        Decrements warehouse stock once for the packing-slip items, propagates
        transfer serials for each source pick list, creates a dispatch record,
        marks the packing slip ``dispatched`` and moves its pick lists to
        ``in_transit``. Requires the packing slip to be in ``loading`` status
        (gate verification is expected to have happened before this call).
        """
        from datetime import UTC, datetime

        from app.models.base import PickListStatus
        from app.models.dispatch_record import DispatchRecord
        from app.models.stock_level import StockLevel
        from app.services.document_numbering_service import DocumentNumberingService
        from app.services.outbound_service import OutboundService

        slip = self._get(slip_id, org_id, for_update=True)
        if slip.status != PackingSlipStatus.LOADING:
            raise ValidationError(
                f"Cannot dispatch packing slip with status '{slip.status.value}' "
                f"(expected 'loading')"
            )

        dispatch_number = DocumentNumberingService(self.db).get_next_number(
            org_id, "dispatch"
        )
        dispatch_record = DispatchRecord(
            organization_id=org_id,
            dispatch_number=dispatch_number,
            pick_list_id=None,
            gate_session_id=None,
            packing_slip_id=slip.id,
            invoice_reference=None,
            vehicle_number=None,
            driver_name=None,
            dispatched_at=datetime.now(UTC),
        )
        self.db.add(dispatch_record)
        self.db.flush()

        # Single stock decrement for packing-slip items (final reconciliation).
        reserved_pick_list_ids = {
            row[0]
            for row in self.db.query(PickList.id)
            .filter(
                PickList.id.in_(
                    {i.pick_list_id for i in slip.items if i.pick_list_id}
                ),
                PickList.reference_type == "outbound_order",
            )
            .all()
        }

        for item in slip.items:
            qty = Decimal(str(item.qty or 0))
            if qty <= 0:
                continue
            stock_level = (
                self.db.query(StockLevel)
                .filter(
                    StockLevel.organization_id == org_id,
                    StockLevel.product_id == item.item_id,
                    StockLevel.warehouse_id == slip.warehouse_id,
                )
                .with_for_update()
                .first()
            )
            if stock_level is not None:
                on_hand = Decimal(str(stock_level.quantity_on_hand or 0))
                stock_level.quantity_on_hand = max(Decimal("0"), on_hand - qty)
                # Only consume the reservation for order-driven pick lists.
                if item.pick_list_id in reserved_pick_list_ids:
                    reserved = Decimal(str(stock_level.quantity_reserved or 0))
                    stock_level.quantity_reserved = max(
                        Decimal("0"), reserved - qty
                    )
                stock_level.quantity_available = max(
                    Decimal("0"),
                    stock_level.quantity_on_hand
                    - (stock_level.quantity_reserved or 0),
                )

        # Propagate transfer serials and advance source pick lists to in_transit.
        outbound = OutboundService(self.db)
        pick_list_ids = {i.pick_list_id for i in slip.items if i.pick_list_id}
        for pl_id in pick_list_ids:
            pl = self.db.get(PickList, pl_id)
            if pl is None or pl.organization_id != org_id:
                continue
            outbound._propagate_transfer_serials(pl, org_id)
            if pl.status not in (
                PickListStatus.IN_TRANSIT,
                PickListStatus.DELIVERED,
            ):
                pl.status = PickListStatus.IN_TRANSIT

        slip.status = PackingSlipStatus.DISPATCHED
        slip.updated_by = user_id

        self.db.commit()
        self.db.refresh(dispatch_record)
        return outbound._to_response(dispatch_record)

    # ------------------------------------------------------------------
    # RESPONSE HELPERS
    # ------------------------------------------------------------------

    def _get(
        self, slip_id: UUID, org_id: UUID, for_update: bool = False
    ) -> PackingSlip:
        query = self.db.query(PackingSlip).filter(
            PackingSlip.id == slip_id,
            PackingSlip.organization_id == org_id,
        )
        if for_update:
            query = query.with_for_update()
        slip = query.first()
        if slip is None:
            raise ResourceNotFoundException(f"Packing slip {slip_id} not found")
        return slip

    def _qseal_context(
        self, slip: PackingSlip, items_by_id: dict[UUID, Item]
    ) -> tuple[dict, dict]:
        """Resolve QSealParameters + QSealTrack lookups for serialized lines only.

        Batch-tracked lines store their batch marker in ``serial_nos`` (not unit
        serials), so they are excluded here — which also avoids the lookup for
        batch-only slips.
        """
        serials = {
            s
            for item in slip.items
            for s in (item.serial_nos or [])
            if s
            and (items_by_id.get(item.item_id) is not None)
            and items_by_id[item.item_id].has_serial_no
        }
        if not serials:
            return {}, {}

        from app.models.qseal import QSealParameters, QSealTrack

        params = (
            self.db.query(
                QSealParameters.serial_number,
                QSealParameters.parent_id,
                QSealParameters.dispatch_batch,
                QSealParameters.manufacturing_date,
                QSealParameters.expiry_date,
            )
            .filter(
                QSealParameters.organization_id == slip.organization_id,
                QSealParameters.serial_number.in_(serials),
            )
            .all()
        )
        param_by_serial = {p.serial_number: p for p in params}

        parent_ids = {p.parent_id for p in params if p.parent_id}
        tracks = (
            self.db.query(QSealTrack)
            .filter(
                QSealTrack.organization_id == slip.organization_id,
                QSealTrack.id.in_(parent_ids),
            )
            .all()
            if parent_ids
            else []
        )
        track_by_id = {t.id: t for t in tracks}
        return param_by_serial, track_by_id

    def _build_groups(
        self,
        slip: PackingSlip,
        items_by_id: dict[UUID, Item],
        param_by_serial: dict,
        track_by_id: dict,
    ) -> list[dict]:
        """Build master-pack groups mirroring the receiving-slip/put-away view."""
        groups: list[dict] = []
        order = 0
        for item in sorted(slip.items, key=lambda i: i.sort_order or 0):
            info = items_by_id.get(item.item_id)
            sku = info.sku if info else None
            product_name = info.item_name if info else None
            is_serialized = bool(info is not None and info.has_serial_no)

            parent_info = None
            group_items: list[dict] = []

            if is_serialized:
                child_serials = [s for s in (item.serial_nos or []) if s]
                parent_id = None
                for serial in child_serials:
                    param = param_by_serial.get(serial)
                    if param and param.parent_id:
                        parent_id = param.parent_id
                        break

                track = track_by_id.get(parent_id) if parent_id else None
                if track is not None:
                    parent_info = {
                        "id": str(track.id),
                        "serial_number": track.serial_number,
                        "name": track.name,
                        "qseal_type": track.qseal_type,
                        "capacity": track.capacity,
                    }

                for serial in child_serials:
                    param = param_by_serial.get(serial)
                    batch = (param.dispatch_batch if param else None) or item.batch_no
                    group_items.append(
                        {
                            "serial_number": serial,
                            "sku": sku,
                            "batch_number": batch or serial,
                            "manufacturing_date": (
                                str(param.manufacturing_date)
                                if param and param.manufacturing_date
                                else None
                            ),
                            "expiry_date": (
                                str(param.expiry_date)
                                if param and param.expiry_date
                                else None
                            ),
                            "quantity": 1,
                            "box_count": 1,
                        }
                    )
            else:
                # Batch-tracked line — keep the full (possibly fractional) qty.
                batch_markers = [s for s in (item.serial_nos or []) if s]
                group_items.append(
                    {
                        "serial_number": None,
                        "sku": sku,
                        "batch_number": item.batch_no
                        or (batch_markers[0] if batch_markers else None),
                        "quantity": float(item.qty or 0),
                        "box_count": 1,
                    }
                )

            groups.append(
                {
                    "parent_qseal": parent_info,
                    "product_name": product_name,
                    "order_id": str(item.order_id) if item.order_id else None,
                    "pick_list_id": str(item.pick_list_id)
                    if item.pick_list_id
                    else None,
                    "bin_location_id": str(item.bin_location_id)
                    if item.bin_location_id
                    else None,
                    "handling_unit_id": str(item.handling_unit_id)
                    if item.handling_unit_id
                    else None,
                    "sort_order": order,
                    "items": group_items,
                }
            )
            order += 1
        return groups

    def _to_response(self, slip: PackingSlip) -> dict:
        items = sorted(slip.items, key=lambda i: i.sort_order or 0)
        item_ids = [i.item_id for i in items]
        items_by_id: dict[UUID, Item] = {}
        if item_ids:
            rows = self.db.query(Item).filter(Item.id.in_(item_ids)).all()
            items_by_id = {r.id: r for r in rows}
        order_ids = sorted({str(i.order_id) for i in items if i.order_id})
        param_by_serial, track_by_id = self._qseal_context(slip, items_by_id)
        groups = self._build_groups(slip, items_by_id, param_by_serial, track_by_id)
        return {
            "id": str(slip.id),
            "organization_id": str(slip.organization_id),
            "packing_slip_no": slip.packing_slip_no,
            "warehouse_id": str(slip.warehouse_id),
            "status": slip.status.value,
            "created_by": str(slip.created_by) if slip.created_by else None,
            "created_at": slip.created_at.isoformat() if slip.created_at else None,
            "updated_at": slip.updated_at.isoformat() if slip.updated_at else None,
            "order_ids": order_ids,
            "items": [
                {
                    "id": str(i.id),
                    "order_id": str(i.order_id) if i.order_id else None,
                    "pick_list_id": str(i.pick_list_id) if i.pick_list_id else None,
                    "item_id": str(i.item_id),
                    "item_name": (
                        items_by_id[i.item_id].item_name
                        if i.item_id in items_by_id
                        else None
                    ),
                    "sku": (
                        items_by_id[i.item_id].sku if i.item_id in items_by_id else None
                    ),
                    "qty": float(i.qty),
                    "uom": i.uom,
                    "per_case_qty": (
                        float(i.per_case_qty) if i.per_case_qty is not None else None
                    ),
                    "case_qty": float(i.case_qty) if i.case_qty is not None else None,
                    "loose_qty": float(i.loose_qty) if i.loose_qty is not None else None,
                    "batch_no": i.batch_no,
                    "bin_location_id": (
                        str(i.bin_location_id) if i.bin_location_id else None
                    ),
                    "handling_unit_id": (
                        str(i.handling_unit_id) if i.handling_unit_id else None
                    ),
                    "sort_order": i.sort_order or 0,
                }
                for i in items
            ],
            "groups": groups,
        }

    def _to_list_item(self, slip: PackingSlip) -> dict:
        order_ids = sorted({str(i.order_id) for i in slip.items if i.order_id})
        return {
            "id": str(slip.id),
            "packing_slip_no": slip.packing_slip_no,
            "warehouse_id": str(slip.warehouse_id),
            "status": slip.status.value,
            "item_count": len(slip.items),
            "order_ids": order_ids,
            "created_at": slip.created_at.isoformat() if slip.created_at else None,
        }
