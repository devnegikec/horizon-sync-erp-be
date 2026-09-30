"""Pick-list reset service (Settings → Data Sync → Reset PickList).

Wipes every artifact generated from an outbound order's pick-list flow so the
order can be re-picked from scratch without re-running the upstream flow
(confirm → generate → pick → dispatch). This is a destructive test/retest
helper and is gated behind the ``organization.update`` permission used by the
on-demand data-sync endpoints.

Scope per pick list:
- restore bin-stock rows for picked units (reverse pick scans)
- reverse the warehouse-level stock effect (release reservation, or restore
  the on-hand decrement taken at dispatch)
- release bin reservations
- clear the internal-transfer ASN serial lines / stock entry / serial history
- delete child rows (scan events, exceptions, idempotency keys, movements,
  dispatch/gate/packing-slip/delivery-note rows)
- delete the pick list and its items
- reset the source outbound order back to ``confirmed``
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError


class PickListResetService:
    """Destructive reset of the pick-list flow for one order / pick list."""

    def __init__(self, db: Session):
        self.db = db

    def reset(
        self,
        organization_id: UUID,
        order_id: UUID | None = None,
        pick_list_id: UUID | None = None,
        order_no: str | None = None,
        pick_list_no: str | None = None,
    ) -> dict:
        """Reset all pick lists for an order (or a single pick list).

        One of ``order_id`` / ``pick_list_id`` / ``order_no`` / ``pick_list_no``
        must be provided. Document numbers (``ORD-...`` / ``PL-...``) are
        resolved to their UUIDs so the UI can drive the reset with human
        readable identifiers.

        The caller owns the transaction (the data-sync flow commits after all
        features run); this method only flushes.
        """
        if not any((order_id, pick_list_id, order_no, pick_list_no)):
            raise ValidationError(
                "Provide one of order_id, pick_list_id, order_no or pick_list_no"
            )

        if order_id is None and order_no:
            order_id = self._resolve_order_id_by_no(organization_id, order_no)

        pick_lists = self._resolve_pick_lists(
            organization_id,
            order_id=order_id,
            pick_list_id=pick_list_id,
            pick_list_no=pick_list_no,
        )

        summary: dict = {
            "pick_lists_reset": 0,
            "orders_reset": 0,
            "details": [],
        }
        # Collect the source order(s) from the pick lists being wiped so the
        # order returns to `confirmed` even when the reset is scoped by
        # pick_list_no / pick_list_id (not just by order).
        order_ids: set[UUID] = set()
        for pl in pick_lists:
            if pl.reference_type == "outbound_order" and pl.reference_id:
                order_ids.add(pl.reference_id)
            summary["details"].append(self._reset_pick_list(pl, organization_id))
            summary["pick_lists_reset"] += 1

        if order_id is not None:
            order_ids.add(order_id)

        for oid in order_ids:
            self._reset_order(oid, organization_id)
            summary["orders_reset"] += 1

        if not pick_lists and not order_ids:
            raise NotFoundError(
                "No pick lists found to reset for the given order/pick list"
            )

        self.db.flush()
        return summary

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def _resolve_order_id_by_no(self, org_id: UUID, order_no: str) -> UUID:
        from app.models.outbound_order import OutboundOrder

        row = (
            self.db.query(OutboundOrder.id)
            .filter(
                OutboundOrder.organization_id == org_id,
                OutboundOrder.order_no == order_no.strip(),
            )
            .first()
        )
        if row is None:
            raise NotFoundError(f"Outbound order not found: {order_no}")
        return row[0]

    def _resolve_pick_lists(
        self,
        org_id: UUID,
        order_id: UUID | None,
        pick_list_id: UUID | None,
        pick_list_no: str | None = None,
    ):
        from app.models.pick_list import PickList

        query = self.db.query(PickList).filter(
            PickList.organization_id == org_id
        )
        if pick_list_id is not None:
            query = query.filter(PickList.id == pick_list_id)
        elif pick_list_no:
            query = query.filter(
                PickList.pick_list_no == pick_list_no.strip()
            )
        else:
            query = query.filter(
                PickList.reference_type == "outbound_order",
                PickList.reference_id == order_id,
            )
        return query.all()

    # ------------------------------------------------------------------
    # Per-pick-list cleanup
    # ------------------------------------------------------------------

    def _reset_pick_list(self, pl, org_id: UUID) -> dict:
        from app.models.base import PickListStatus

        # On-hand stock is decremented only at dispatch (IN_TRANSIT/DELIVERED/
        # COMPLETED). READY_FOR_DISPATCH still means picked-but-undispatched,
        # so its warehouse reservation must be released rather than on-hand
        # restored.
        was_dispatched = pl.status in (
            PickListStatus.IN_TRANSIT,
            PickListStatus.DELIVERED,
            PickListStatus.COMPLETED,
        )

        self._restore_bin_stock(pl, org_id)
        self._restore_warehouse_stock(pl, org_id, was_dispatched)
        self._clear_transfer_asn(pl, org_id)
        self._delete_children(pl, org_id)

        pick_list_no = pl.pick_list_no
        self.db.query(type(pl)).filter_by(id=pl.id).delete(
            synchronize_session=False
        )
        return {"pick_list_no": pick_list_no, "status": pl.status.value}

    def _restore_bin_stock(self, pl, org_id: UUID) -> None:
        """Put picked units back into their source bins as available stock."""
        from app.models.bin_stock_level import BinStockLevel, InventoryStatus

        for item in pl.items:
            picked = Decimal(str(item.picked_qty or 0))
            if picked <= 0 or item.bin_location_id is None:
                continue

            serials = [s for s in (item.serial_nos or []) if s]
            if serials:
                # Unit-level QR serials live one row per serial; restore each
                # row to available / qty 1.
                rows = (
                    self.db.query(BinStockLevel)
                    .filter(
                        BinStockLevel.organization_id == org_id,
                        BinStockLevel.bin_location_id == item.bin_location_id,
                        BinStockLevel.item_id == item.item_id,
                        BinStockLevel.batch_number.in_(serials),
                    )
                    .all()
                )
                for row in rows:
                    row.inventory_status = InventoryStatus.AVAILABLE.value
                    row.quantity_on_hand = Decimal("1")
                continue

            # Batch-tracked: restore the picked quantity to the batch row.
            rows = (
                self.db.query(BinStockLevel)
                .filter(
                    BinStockLevel.organization_id == org_id,
                    BinStockLevel.bin_location_id == item.bin_location_id,
                    BinStockLevel.item_id == item.item_id,
                    BinStockLevel.batch_number == item.batch_no,
                )
                .all()
            )
            if rows:
                for row in rows:
                    row.inventory_status = InventoryStatus.AVAILABLE.value
                    row.quantity_on_hand = (
                        Decimal(str(row.quantity_on_hand or 0)) + picked
                    )
            else:
                from app.services.bin_stock_service import BinStockService

                BinStockService(self.db).add_stock(
                    bin_id=item.bin_location_id,
                    item_id=item.item_id,
                    quantity=picked,
                    org_id=org_id,
                    batch_number=item.batch_no,
                    sync_warehouse=False,
                )

    def _restore_warehouse_stock(
        self, pl, org_id: UUID, was_dispatched: bool
    ) -> None:
        """Reverse the warehouse stock-level effect of the pick list."""
        from app.models.stock_level import StockLevel

        picked_by_item: dict[UUID, Decimal] = {}
        reserved_by_item: dict[UUID, Decimal] = {}
        warehouse_by_item: dict[UUID, UUID] = {}
        for item in pl.items:
            picked_by_item[item.item_id] = picked_by_item.get(
                item.item_id, Decimal("0")
            ) + Decimal(str(item.picked_qty or 0))
            reserved_by_item[item.item_id] = reserved_by_item.get(
                item.item_id, Decimal("0")
            ) + Decimal(str(item.qty or 0))
            warehouse_by_item.setdefault(item.item_id, item.warehouse_id)

        for item_id, warehouse_id in warehouse_by_item.items():
            stock_level = (
                self.db.query(StockLevel)
                .filter(
                    StockLevel.organization_id == org_id,
                    StockLevel.product_id == item_id,
                    StockLevel.warehouse_id == warehouse_id,
                )
                .with_for_update()
                .first()
            )
            if stock_level is None:
                continue

            on_hand = Decimal(str(stock_level.quantity_on_hand or 0))
            reserved = Decimal(str(stock_level.quantity_reserved or 0))
            if was_dispatched:
                # Reverse the dispatch-time on-hand decrement. The reservation
                # was consumed at dispatch, so it is not re-released here.
                on_hand += picked_by_item.get(item_id, Decimal("0"))
            else:
                # Release the reservation taken at pick-list generation. Only
                # order-driven pick lists reserve warehouse stock; legacy/
                # invoice pick lists never did, so releasing for them would
                # consume another pick list's reservation.
                if pl.reference_type == "outbound_order":
                    reserved = max(
                        Decimal("0"),
                        reserved - reserved_by_item.get(item_id, Decimal("0")),
                    )
                on_hand = Decimal(str(stock_level.quantity_on_hand or 0))

            stock_level.quantity_on_hand = on_hand
            stock_level.quantity_reserved = reserved
            stock_level.quantity_available = max(
                Decimal("0"), on_hand - reserved
            )

    def _clear_transfer_asn(self, pl, org_id: UUID) -> None:
        """Remove the serial lines / stock entry written to the transfer ASN."""
        from app.models.asn_order import AsnOrder, AsnOrderSerialLine
        from app.models.serial_no import SerialNo, SerialNoHistory
        from app.models.stock_entry import StockEntry, StockEntryItem

        asn = self._resolve_transfer_asn(pl, org_id)
        if asn is None or asn.asn_type != "internal_transfer":
            return

        serial_lines = (
            self.db.query(AsnOrderSerialLine)
            .filter(AsnOrderSerialLine.asn_order_id == asn.id)
            .all()
        )

        # Reset serial rows that were marked in_transit by the transfer_out.
        serials_by_item: dict[UUID, list[str]] = {}
        for line in serial_lines:
            serials_by_item.setdefault(line.item_id, []).append(line.serial_no)
        for item_id, serials in serials_by_item.items():
            self.db.query(SerialNo).filter(
                SerialNo.organization_id == org_id,
                SerialNo.item_id == item_id,
                SerialNo.serial_no.in_(serials),
            ).update(
                {"status": "in_stock", "warehouse_id": asn.warehouse_id_from},
                synchronize_session=False,
            )

        # Remove chain-of-custody rows for this ASN (transfer_out and any
        # transfer_in already captured at the destination).
        self.db.query(SerialNoHistory).filter(
            SerialNoHistory.organization_id == org_id,
            SerialNoHistory.transaction_id == asn.id,
            SerialNoHistory.transaction_type.in_(["transfer_out", "transfer_in"]),
        ).delete(synchronize_session=False)

        # Drop the serial lines and the linked material-transfer stock entry.
        self.db.query(AsnOrderSerialLine).filter(
            AsnOrderSerialLine.asn_order_id == asn.id
        ).delete(synchronize_session=False)

        stock_entry_ids = [
            row[0]
            for row in self.db.query(StockEntry.id)
            .filter(
                StockEntry.organization_id == org_id,
                StockEntry.reference_type == "asn_order",
                StockEntry.reference_id == asn.id,
            )
            .all()
        ]
        if stock_entry_ids:
            self.db.query(StockEntryItem).filter(
                StockEntryItem.stock_entry_id.in_(stock_entry_ids)
            ).delete(synchronize_session=False)
            self.db.query(StockEntry).filter(
                StockEntry.id.in_(stock_entry_ids)
            ).delete(synchronize_session=False)

        asn.serialization_mode = None
        asn.linked_stock_entry_id = None
        if asn.linked_pick_list_id == pl.id:
            asn.linked_pick_list_id = None

    def _resolve_transfer_asn(self, pl, org_id: UUID):
        from app.models.asn_order import AsnOrder
        from app.models.outbound_order import OutboundOrder

        asn_order_id = None
        if pl.reference_type == "asn_order" and pl.reference_id:
            asn_order_id = pl.reference_id
        elif pl.reference_type == "outbound_order" and pl.reference_id:
            order = self.db.get(OutboundOrder, pl.reference_id)
            if (
                order is not None
                and order.reference_type == "asn_order"
                and order.reference_id
            ):
                asn_order_id = order.reference_id

        if asn_order_id is None:
            return None
        return (
            self.db.query(AsnOrder)
            .filter(
                AsnOrder.id == asn_order_id,
                AsnOrder.organization_id == org_id,
            )
            .first()
        )

    def _delete_children(self, pl, org_id: UUID) -> None:
        """Delete all rows that reference this pick list."""
        from app.models.bin_reservation import BinReservation
        from app.models.delivery_note import DeliveryNote, DeliveryNoteItem
        from app.models.dispatch_record import DispatchRecord
        from app.models.erp_sync_message import ErpSyncMessage
        from app.models.gate_verification import (
            GateVerificationItem,
            GateVerificationSession,
        )
        from app.models.packing_slip import PackingSlip, PackingSlipItem
        from app.models.pick_exception import PickException, PickExceptionAudit
        from app.models.pick_idempotency import PickIdempotencyKey
        from app.models.pick_list import PickListItem
        from app.models.qr_scan_event import QRScanEvent
        from app.models.stock_movement import StockMovement

        pl_id = pl.id
        pl_id_str = str(pl_id)

        # Exception audit first (FK → pick_exceptions).
        exception_ids = [
            row[0]
            for row in self.db.query(PickException.id)
            .filter(PickException.pick_list_id == pl_id)
            .all()
        ]
        if exception_ids:
            self.db.query(PickExceptionAudit).filter(
                PickExceptionAudit.exception_id.in_(exception_ids)
            ).delete(synchronize_session=False)
        self.db.query(PickException).filter(
            PickException.pick_list_id == pl_id
        ).delete(synchronize_session=False)

        self.db.query(PickIdempotencyKey).filter(
            PickIdempotencyKey.pick_list_id == pl_id
        ).delete(synchronize_session=False)

        self.db.query(ErpSyncMessage).filter(
            ErpSyncMessage.pick_list_id == pl_id
        ).delete(synchronize_session=False)

        # Pick-scan events and their movement ledger rows. ``extra_data`` is a
        # TypeDecorator over JSON, so the Postgres-only ``.astext`` accessor is
        # unavailable — query the stored key with the ``->>`` operator instead.
        scan_event_ids = [
            row[0]
            for row in self.db.query(QRScanEvent.id)
            .filter(
                text(
                    "qr_scan_events.extra_data ->> 'pick_list_id' = :pick_list_id"
                ).bindparams(pick_list_id=pl_id_str)
            )
            .all()
        ]
        if scan_event_ids:
            self.db.query(StockMovement).filter(
                StockMovement.organization_id == org_id,
                StockMovement.reference_type.in_(["pick_scan", "pick"]),
                StockMovement.reference_id.in_(scan_event_ids),
            ).delete(synchronize_session=False)
            self.db.query(QRScanEvent).filter(
                QRScanEvent.id.in_(scan_event_ids)
            ).delete(synchronize_session=False)

        # Dispatch and gate-session rows. Break the circular
        # pick_list.dispatch_record_id -> dispatch_records.id FK first.
        if getattr(pl, "dispatch_record_id", None) is not None:
            pl.dispatch_record_id = None
            self.db.flush()
        self.db.query(DispatchRecord).filter(
            DispatchRecord.pick_list_id == pl_id
        ).delete(synchronize_session=False)

        gate_session_ids = [
            row[0]
            for row in self.db.query(GateVerificationSession.id)
            .filter(GateVerificationSession.pick_list_id == pl_id)
            .all()
        ]
        if gate_session_ids:
            self.db.query(GateVerificationItem).filter(
                GateVerificationItem.gate_session_id.in_(gate_session_ids)
            ).delete(synchronize_session=False)
        self.db.query(GateVerificationSession).filter(
            GateVerificationSession.pick_list_id == pl_id
        ).delete(synchronize_session=False)

        # Packing slip + delivery note line items. A slip can pack multiple
        # pick lists, so remove this pick list's items first, then drop any
        # parent slip left with no remaining items.
        packing_slip_ids = [
            row[0]
            for row in self.db.query(PackingSlipItem.packing_slip_id)
            .filter(PackingSlipItem.pick_list_id == pl_id)
            .distinct()
            .all()
        ]
        self.db.query(PackingSlipItem).filter(
            PackingSlipItem.pick_list_id == pl_id
        ).delete(synchronize_session=False)
        if packing_slip_ids:
            remaining_slip_ids = {
                row[0]
                for row in self.db.query(PackingSlipItem.packing_slip_id)
                .filter(PackingSlipItem.packing_slip_id.in_(packing_slip_ids))
                .all()
            }
            empty_slip_ids = [
                sid for sid in packing_slip_ids if sid not in remaining_slip_ids
            ]
            if empty_slip_ids:
                self.db.query(PackingSlip).filter(
                    PackingSlip.id.in_(empty_slip_ids)
                ).delete(synchronize_session=False)

        delivery_note_ids = [
            row[0]
            for row in self.db.query(DeliveryNote.id)
            .filter(DeliveryNote.pick_list_id == pl_id)
            .all()
        ]
        if delivery_note_ids:
            self.db.query(DeliveryNoteItem).filter(
                DeliveryNoteItem.delivery_note_id.in_(delivery_note_ids)
            ).delete(synchronize_session=False)
            self.db.query(DeliveryNote).filter(
                DeliveryNote.id.in_(delivery_note_ids)
            ).delete(synchronize_session=False)

        # Bin reservations and pick list items.
        self.db.query(BinReservation).filter(
            BinReservation.task_id == pl_id,
            BinReservation.task_type == "pick",
        ).delete(synchronize_session=False)

        self.db.query(PickListItem).filter(
            PickListItem.pick_list_id == pl_id
        ).delete(synchronize_session=False)

    def _reset_order(self, order_id: UUID, org_id: UUID) -> None:
        """Return the source order to ``confirmed`` so it can be re-picked.

        Only reverts the order when no pick lists remain for it (otherwise a
        scoped reset of one pick list would leave a sibling pick list stuck on
        a reverted order).
        """
        from app.models.base import OutboundOrderStatus
        from app.models.outbound_order import OutboundOrder
        from app.models.pick_list import PickList

        remaining = (
            self.db.query(PickList.id)
            .filter(
                PickList.organization_id == org_id,
                PickList.reference_type == "outbound_order",
                PickList.reference_id == order_id,
            )
            .count()
        )
        if remaining > 0:
            return

        order = (
            self.db.query(OutboundOrder)
            .filter(
                OutboundOrder.id == order_id,
                OutboundOrder.organization_id == org_id,
            )
            .first()
        )
        if order is None:
            return
        # Only revert orders that have actually progressed past confirmation
        # (i.e. a pick list existed for them). Draft/confirmed orders with no
        # pick lists are left untouched.
        if order.status not in (
            OutboundOrderStatus.PENDING_PICKING,
            OutboundOrderStatus.COMPLETED,
        ):
            return
        order.status = OutboundOrderStatus.CONFIRMED
