"""Put-away service for generating optimized put-away lists from receiving slips.

Handles:
- Generating put-away lists from approved receiving slips
- Assigning bins respecting allocations (exclusive first, then preferred, then unallocated)
- Filtering bins by capacity
- Splitting across bins if single bin insufficient
- Completing put-away items (updating bin stock)
- Skipping put-away items with reason
- Triggering capacity rollup on item completion
- Updating receiving slip to PUTAWAY_COMPLETE when all items done

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 20.3, 20.4, 20.5, 20.6
"""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.bin_stock_level import BinStockLevel
from app.models.item import Item
from app.models.location_allocation import LocationAllocation
from app.models.put_away_list import PutAwayList, PutAwayListItem
from app.models.receiving_slip import ReceivingSlip
from app.models.warehouse_location import WarehouseLocation
from app.services.bin_capacity_service import BinCapacityService
from app.services.bin_reservation_service import BinReservationService
from app.services.bin_stock_service import BinStockService
from app.services.capacity_service import CapacityService
from app.services.routing_optimizer import BinLocation, RoutingOptimizer
from app.services.volumetric_assignment_service import VolumetricAssignmentService


class PutAwayService:
    """Service for generating and managing put-away lists from receiving slips."""

    def __init__(self, db: Session):
        self.db = db
        self.bin_stock_service = BinStockService(db)
        self.capacity_service = CapacityService(db)
        self.routing_optimizer = RoutingOptimizer()
        self.reservation_service = BinReservationService(db)

    # ── Direct Put-Away reconciliation ──────────────────────────────────

    def create_direct_list(
        self,
        organization_id: UUID,
        warehouse_id: UUID,
        created_by: UUID | None = None,
    ) -> PutAwayList:
        """Create an empty put-away list for a direct put-away session."""
        from app.services.document_numbering_service import DocumentNumberingService

        number = DocumentNumberingService(self.db).get_next_number(
            organization_id, "put_away_list"
        )
        pal = PutAwayList(
            organization_id=organization_id,
            warehouse_id=warehouse_id,
            put_away_list_no=number,
            status="pending",
            reference_type="direct_putaway",
            created_by=created_by,
        )
        self.db.add(pal)
        self.db.commit()
        self.db.refresh(pal)
        return pal

    def add_direct_completed_item(
        self, tracking, list_id: UUID
    ) -> PutAwayListItem | None:
        """Attach a completed tracking row to a direct put-away list (idempotent)."""
        pal = self.db.query(PutAwayList).filter(PutAwayList.id == list_id).first()
        if pal is None:
            raise NotFoundError(
                message="Put-away list not found",
                entity_type="PutAwayList",
                entity_id=str(list_id),
            )

        # Idempotent: reuse the item already created for this tracking row
        if tracking.put_away_item_id:
            existing = self.db.get(PutAwayListItem, tracking.put_away_item_id)
            if existing is not None:
                return existing

        item = PutAwayListItem(
            organization_id=tracking.organization_id,
            put_away_list_id=list_id,
            item_id=tracking.item_id,
            sku=tracking.sku,
            batch_number=tracking.qr_identifier,
            quantity=tracking.quantity,
            bin_location_id=tracking.bin_location_id,
            status="completed",
            completed_at=datetime.now(UTC),
        )
        self.db.add(item)
        self.db.flush()

        tracking.put_away_list_id = list_id
        tracking.put_away_item_id = item.id

        # Mark the list complete once all items are completed
        pending = (
            self.db.query(PutAwayListItem)
            .filter(
                PutAwayListItem.put_away_list_id == list_id,
                PutAwayListItem.status != "completed",
            )
            .count()
        )
        if pending == 0:
            pal.status = "completed"
            pal.completed_at = datetime.now(UTC)

        self.db.commit()
        return item

    def reconcile_tracking_with_recent_slip(
        self,
        tracking,
        organization_id: UUID,
        within_hours: int = 24,
    ):
        """Link a completed tracking row to a matching receiving slip (≤24h)."""
        from app.models.receiving_slip import ReceivingSlipItem

        cutoff = datetime.now(UTC) - timedelta(hours=within_hours)
        slip_item = (
            self.db.query(ReceivingSlipItem)
            .join(ReceivingSlip, ReceivingSlip.id == ReceivingSlipItem.slip_id)
            .filter(
                ReceivingSlipItem.batch_number == tracking.qr_identifier,
                ReceivingSlipItem.organization_id == organization_id,
                ReceivingSlip.created_at >= cutoff,
            )
            .order_by(ReceivingSlip.created_at.desc())
            .first()
        )
        if slip_item is None:
            return None

        tracking.receiving_slip_id = slip_item.slip_id
        slip_item.put_away_status = "completed"
        slip_item.bin_location_id = tracking.bin_location_id
        slip_item.put_away_at = tracking.putaway_at or datetime.now(UTC)

        if tracking.put_away_list_id:
            pal = (
                self.db.query(PutAwayList)
                .filter(PutAwayList.id == tracking.put_away_list_id)
                .first()
            )
            if pal is not None and pal.receiving_slip_id is None:
                pal.receiving_slip_id = slip_item.slip_id

        self.db.flush()
        # If this was the last pending item, advance the slip status.
        if self.all_slip_items_put_away(slip_item.slip_id):
            self.mark_slip_putaway_complete(slip_item.slip_id)
        self.db.commit()
        return slip_item

    def reconcile_slip_with_completed_putaway(self, slip, organization_id: UUID) -> int:
        """After a receiving slip is created, link items already put away via
        direct put-away (matched by QR identifier == batch_number)."""
        from app.models.receiving_slip import ReceivingSlipItem
        from app.models.scanned_item_tracking import ScannedItemTracking

        slip_items = (
            self.db.query(ReceivingSlipItem)
            .filter(ReceivingSlipItem.slip_id == slip.id)
            .all()
        )

        linked = 0
        for slip_item in slip_items:
            # Only reconcile accepted items. Rejected/floating items are left
            # for the warehouse manager to resolve manually.
            if slip_item.flag != "ok":
                continue

            tracking = (
                self.db.query(ScannedItemTracking)
                .filter(
                    ScannedItemTracking.qr_identifier == slip_item.batch_number,
                    ScannedItemTracking.organization_id == organization_id,
                    ScannedItemTracking.putaway_status == "completed",
                )
                .first()
            )
            if tracking is None:
                continue

            tracking.receiving_slip_id = slip.id
            slip_item.put_away_status = "completed"
            slip_item.bin_location_id = tracking.bin_location_id
            slip_item.put_away_at = tracking.putaway_at or datetime.now(UTC)

            # Approve the receiving axis and enter stock now that both axes are
            # complete (direct put-away happened before the receiving slip).
            from app.services.scanned_item_tracking_service import (
                ScannedItemTrackingService,
            )

            ScannedItemTrackingService(self.db).approve_tracking_row(tracking)

            if tracking.put_away_list_id:
                pal = (
                    self.db.query(PutAwayList)
                    .filter(PutAwayList.id == tracking.put_away_list_id)
                    .first()
                )
                if pal is not None and pal.receiving_slip_id is None:
                    pal.receiving_slip_id = slip.id
            linked += 1

        if linked:
            self.db.commit()
        return linked

    def all_slip_items_put_away(self, slip_id: UUID) -> bool:
        """Return True when every accepted receiving-slip item has been binned."""
        from app.models.receiving_slip import ReceivingSlipItem

        accepted = (
            self.db.query(ReceivingSlipItem)
            .filter(
                ReceivingSlipItem.slip_id == slip_id,
                ReceivingSlipItem.flag == "ok",
            )
            .all()
        )
        return bool(accepted) and all(
            item.put_away_status == "completed" for item in accepted
        )

    def mark_slip_putaway_complete(self, slip_id: UUID) -> bool:
        """Advance a pending_putaway receiving slip to putaway_complete."""
        slip = self.db.query(ReceivingSlip).filter(ReceivingSlip.id == slip_id).first()
        if slip is None or slip.status != "pending_putaway":
            return False
        slip.status = "putaway_complete"
        slip.updated_at = datetime.now(UTC)
        self.db.flush()
        # Put-away is the terminal step of receiving — refresh ASN delivered
        # quantities and delivery status so the ASN closes out correctly.
        if slip.asn_order_id:
            from app.services.inbound_service import InboundService

            InboundService(self.db)._sync_asn_delivered_qty(
                slip.asn_order_id, slip.organization_id
            )
        return True

    def generate_from_slip(
        self,
        slip_id: UUID,
        org_id: UUID,
        worker_id: UUID | None = None,
        mode: str | None = None,
    ) -> PutAwayList:
        """Generate a put-away list from an approved receiving slip.

        ``mode='auto'`` (default) assigns bins respecting allocations (exclusive
        first, then preferred, then unallocated) and capacity, groups items by
        zone/aisle and sorts by optimal traversal order. ``mode='manual'``
        creates the list with items grouped by SKU but leaves ``bin_location_id``
        empty so workers assign bins themselves during completion.

        Creates a worker task via TaskService if a worker_id is provided.

        Args:
            slip_id: The receiving slip ID to generate put-away from.
            org_id: Organization ID for scoping.
            worker_id: Optional worker ID to assign the put-away task to.
            mode: 'auto' or 'manual'; None falls back to the organization's
                ``putaway_mode`` setting.

        Returns:
            The created PutAwayList with items assigned to bins.

        Raises:
            NotFoundError: If receiving slip is not found.
            StateError: If slip is not in pending_putaway status.

        Requirements: 8.1, 8.2, 8.3, 8.4, 20.3, 20.4, 20.5, 20.6
        """
        mode = self._resolve_putaway_mode(org_id, mode)
        slip = self._get_pending_putaway_slip(slip_id, org_id)
        self._ensure_no_existing_list(slip)
        if worker_id is not None:
            self._validate_worker(worker_id, slip.warehouse_id, org_id)
        item_specs, warnings_parts = self._build_put_away_specs(slip, org_id, mode)

        from app.services.document_numbering_service import DocumentNumberingService

        put_away_number = DocumentNumberingService(self.db).get_next_number(
            org_id, "put_away_list"
        )
        return self._create_list_from_specs(
            slip=slip,
            org_id=org_id,
            mode=mode,
            item_specs=item_specs,
            worker_id=worker_id,
            warnings_parts=warnings_parts,
            put_away_number=put_away_number,
        )

    def generate_from_slip_for_workers(
        self,
        slip_id: UUID,
        org_id: UUID,
        worker_ids: list[UUID],
        mode: str | None = None,
    ) -> list[PutAwayList]:
        """Generate one put-away list per worker, distributing slip items.

        Splits the eligible slip lines across the given workers (round-robin)
        and creates a separate PutAwayList for each worker, each assigned to
        that worker and accompanied by a worker task.

        Args:
            slip_id: The receiving slip ID to generate put-away from.
            org_id: Organization ID for scoping.
            worker_ids: Workers to distribute the put-away work across.
            mode: 'auto' or 'manual'; None falls back to the organization's
                ``putaway_mode`` setting.

        Returns:
            One PutAwayList per worker that received at least one item.
        """
        mode = self._resolve_putaway_mode(org_id, mode)
        slip = self._get_pending_putaway_slip(slip_id, org_id)
        self._ensure_no_existing_list(slip)
        item_specs, warnings_parts = self._build_put_away_specs(slip, org_id, mode)

        from app.services.document_numbering_service import DocumentNumberingService

        numbering = DocumentNumberingService(self.db)
        workers = [w for w in worker_ids if w is not None]
        for worker_id in workers:
            self._validate_worker(worker_id, slip.warehouse_id, org_id)

        # No workers supplied → fall back to a single unassigned list.
        if not workers:
            number = numbering.get_next_number(org_id, "put_away_list")
            return [
                self._create_list_from_specs(
                    slip=slip,
                    org_id=org_id,
                    mode=mode,
                    item_specs=item_specs,
                    worker_id=None,
                    warnings_parts=warnings_parts,
                    put_away_number=number,
                )
            ]

        # Keep all children of the same master-pack (parent) on one worker so a
        # physical carton is not split across multiple put-away lists.
        groups = self._group_specs_by_parent(item_specs, org_id)
        chunks = self._distribute_round_robin(groups, len(workers))
        lists: list[PutAwayList] = []
        for worker_id, chunk in zip(workers, chunks):
            if not chunk:
                # More workers than groups — skip empty chunks.
                continue
            worker_specs = [spec for group in chunk for spec in group]
            number = numbering.get_next_number(org_id, "put_away_list")
            lists.append(
                self._create_list_from_specs(
                    slip=slip,
                    org_id=org_id,
                    mode=mode,
                    item_specs=worker_specs,
                    worker_id=worker_id,
                    warnings_parts=warnings_parts,
                    put_away_number=number,
                )
            )

        # Nothing eligible (all lines skipped) — still return a single list so
        # the caller sees the warnings, mirroring single-worker behaviour.
        if not lists:
            number = numbering.get_next_number(org_id, "put_away_list")
            lists.append(
                self._create_list_from_specs(
                    slip=slip,
                    org_id=org_id,
                    mode=mode,
                    item_specs=[],
                    worker_id=None,
                    warnings_parts=warnings_parts,
                    put_away_number=number,
                )
            )
        return lists

    # ── Put-away generation helpers ─────────────────────────────────────────

    @staticmethod
    def _distribute_round_robin(items: list, count: int) -> list[list]:
        """Distribute items across ``count`` buckets round-robin."""
        buckets: list[list] = [[] for _ in range(count)]
        for idx, item in enumerate(items):
            buckets[idx % count].append(item)
        return buckets

    def _group_specs_by_parent(
        self, item_specs: list[dict], org_id: UUID
    ) -> list[list[dict]]:
        """Group put-away specs so children of the same master-pack stay together.

        Child serials are stored in each spec's ``batch_number``; their shared
        parent box is resolved via ``qseal_parameters.parent_id``. Specs without
        a parent (or without a resolvable child serial) are each treated as an
        individual group so they can still be distributed across workers.
        """
        from app.models.qseal import QSealParameters

        batch_numbers = {
            s.get("batch_number") for s in item_specs if s.get("batch_number")
        }
        parent_by_batch: dict[str, UUID | None] = {}
        if batch_numbers:
            rows = (
                self.db.query(QSealParameters.serial_number, QSealParameters.parent_id)
                .filter(
                    QSealParameters.serial_number.in_(batch_numbers),
                    QSealParameters.organization_id == org_id,
                )
                .all()
            )
            parent_by_batch = {sn: pid for sn, pid in rows if pid}

        groups: dict[str, list[dict]] = {}
        for spec in item_specs:
            batch = spec.get("batch_number")
            parent_id = parent_by_batch.get(batch) if batch else None
            if parent_id:
                key = f"parent:{parent_id}"
            else:
                key = f"item:{batch or id(spec)}"
            groups.setdefault(key, []).append(spec)

        return list(groups.values())

    def _resolve_putaway_mode(self, org_id: UUID, mode: str | None) -> str:
        if mode is None:
            from app.services.pick_settings_service import PickSettingsService

            mode = str(PickSettingsService(self.db).get_value(org_id, "putaway_mode"))
        if mode not in {"auto", "manual"}:
            raise ValidationError(f"Invalid put-away generation mode: {mode}")
        return mode

    def _get_pending_putaway_slip(self, slip_id: UUID, org_id: UUID) -> ReceivingSlip:
        slip = (
            self.db.query(ReceivingSlip)
            .filter(
                ReceivingSlip.id == slip_id,
                ReceivingSlip.organization_id == org_id,
            )
            .with_for_update()
            .first()
        )
        if slip is None:
            raise NotFoundError(
                message="Receiving slip not found",
                entity_type="ReceivingSlip",
                entity_id=str(slip_id),
            )
        if slip.status != "pending_putaway":
            raise StateError(
                message="Receiving slip must be in pending_putaway status to generate put-away list",
                current_state=slip.status,
                required_state=["pending_putaway"],
            )
        return slip

    def _ensure_no_existing_list(self, slip: ReceivingSlip) -> None:
        """Reject generation when a put-away list already exists for the slip."""
        existing = (
            self.db.query(PutAwayList)
            .filter(
                PutAwayList.receiving_slip_id == slip.id,
                PutAwayList.reference_type == "receiving_slip",
            )
            .first()
        )
        if existing is not None:
            raise ValidationError(
                f"Put-away list '{existing.put_away_list_no}' already exists "
                f"for receiving slip '{slip.slip_number}'"
            )

    def _validate_worker(
        self, worker_id: UUID, warehouse_id: UUID, org_id: UUID
    ) -> None:
        """Reject workers that are nonexistent, inactive, cross-org, or not
        assigned to this warehouse before they are persisted on a list/task."""
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

    def _build_put_away_specs(
        self, slip: ReceivingSlip, org_id: UUID, mode: str
    ) -> tuple[list[dict], list[str]]:
        """Resolve eligible slip lines into put-away item specs (no ORM yet).

        Returns (item_specs, warnings_parts) where each spec is a dict with
        keys item_id, sku, batch_number, quantity, bin_location_id.
        """
        item_specs: list[dict] = []
        manual_grouped: dict[tuple[str, str | None], dict] = {}
        skipped_damaged: list[str] = []
        skipped_rejected: list[str] = []
        skipped_exception: list[str] = []
        skipped_unresolved: list[str] = []

        for slip_item in slip.items:
            # Only fully accepted, good receipt lines enter normal put-away.
            # HOLD, QUARANTINE, and EXCESS are physically segregated and
            # require an explicit manager disposition before release.
            if slip_item.flag in (
                "damaged",
                "rejected",
                "hold",
                "quarantine",
                "excess",
            ):
                if slip_item.flag in ("hold", "quarantine", "excess"):
                    skipped_exception.append(
                        f"{slip_item.sku} (batch: {slip_item.batch_number}, qty: {slip_item.quantity}, flag: {slip_item.flag})"
                    )
                    continue
                skipped = (
                    skipped_damaged if slip_item.flag == "damaged" else skipped_rejected
                )
                skipped.append(
                    f"{slip_item.sku} (batch: {slip_item.batch_number}, qty: {slip_item.quantity})"
                )
                continue

            # Resolve item from SKU with deterministic priority (item_code →
            # sku → gtin). QR-product-linked slip items may store the GTIN in
            # the sku field, so gtin remains included for compatibility.
            item = self._resolve_item_by_sku(slip_item.sku, org_id)
            if item is None:
                skipped_unresolved.append(
                    f"{slip_item.sku} (batch: {slip_item.batch_number})"
                )
                continue

            quantity = Decimal(str(slip_item.quantity))

            # Manual mode: leave bin assignment to the worker. Items are
            # grouped by (SKU, batch) so repeated slip lines merge into one
            # list item instead of producing duplicate rows.
            if mode == "manual":
                key = (slip_item.sku, slip_item.batch_number)
                existing = manual_grouped.get(key)
                if existing is not None:
                    existing["quantity"] += quantity
                else:
                    manual_grouped[key] = {
                        "item_id": item.id,
                        "sku": slip_item.sku,
                        "batch_number": slip_item.batch_number,
                        "quantity": quantity,
                        "bin_location_id": None,
                    }
                continue

            bin_assignments = self._assign_bins(
                item_id=item.id,
                item_group_id=item.item_group_id,
                quantity=quantity,
                warehouse_id=slip.warehouse_id,
                org_id=org_id,
            )
            for assignment in bin_assignments:
                item_specs.append(
                    {
                        "item_id": item.id,
                        "sku": slip_item.sku,
                        "batch_number": slip_item.batch_number,
                        "quantity": assignment["quantity"],
                        "bin_location_id": assignment["bin_location_id"],
                    }
                )

        if manual_grouped:
            item_specs.extend(manual_grouped.values())

        warnings_parts: list[str] = []
        if skipped_damaged:
            warnings_parts.append(
                f"Skipped {len(skipped_damaged)} damaged item(s): "
                + "; ".join(skipped_damaged)
            )
        if skipped_rejected:
            warnings_parts.append(
                f"Skipped {len(skipped_rejected)} rejected item(s): "
                + "; ".join(skipped_rejected)
            )
        if skipped_exception:
            warnings_parts.append(
                f"Skipped {len(skipped_exception)} held/quarantined/excess item(s): "
                + "; ".join(skipped_exception)
            )
        if skipped_unresolved:
            warnings_parts.append(
                f"Skipped {len(skipped_unresolved)} item(s) with unknown SKU (no matching Item found): "
                + "; ".join(skipped_unresolved)
            )

        return item_specs, warnings_parts

    def _create_list_from_specs(
        self,
        slip: ReceivingSlip,
        org_id: UUID,
        mode: str,
        item_specs: list[dict],
        worker_id: UUID | None,
        warnings_parts: list[str],
        put_away_number: str,
    ) -> PutAwayList:
        """Persist one PutAwayList and its items from pre-built specs."""
        put_away_list = PutAwayList(
            organization_id=org_id,
            warehouse_id=slip.warehouse_id,
            put_away_list_no=put_away_number,
            status="pending",
            reference_type="receiving_slip",
            reference_id=slip.id,
            receiving_slip_id=slip.id,
        )
        self.db.add(put_away_list)
        self.db.flush()

        put_away_items: list[PutAwayListItem] = []
        for idx, spec in enumerate(item_specs):
            put_away_item = PutAwayListItem(
                organization_id=org_id,
                put_away_list_id=put_away_list.id,
                item_id=spec["item_id"],
                sku=spec["sku"],
                batch_number=spec["batch_number"],
                quantity=spec["quantity"],
                bin_location_id=spec["bin_location_id"],
                sort_order=idx if mode == "manual" else 0,
                status="pending",
            )
            self.db.add(put_away_item)
            put_away_items.append(put_away_item)

        if warnings_parts:
            put_away_list.remarks = json.dumps({"warnings": warnings_parts})

        self.db.flush()

        if mode == "auto":
            # Volumetric bin assignment — runs in the same transaction (Req 7.1, 7.6, 7.7)
            volumetric_service = VolumetricAssignmentService()
            volumetric_service.assign_bins(
                put_away_list_items=put_away_list.items,
                warehouse_id=slip.warehouse_id,
                org_id=org_id,
                db=self.db,
            )
            self.db.flush()

            # Optimize routing order for all put-away items
            self._optimize_item_routing(put_away_items)

        # Assign worker if provided
        if worker_id is not None:
            put_away_list.assigned_to = worker_id

        self.db.commit()

        # Create a worker task via TaskService if worker_id is provided
        if worker_id is not None:
            from app.services.task_service import TaskService

            task_service = TaskService(self.db)
            task_service.create_task(
                task_type="put_away",
                worker_id=worker_id,
                reference_id=put_away_list.id,
                org_id=org_id,
            )

        self.db.refresh(put_away_list)
        return put_away_list

    def enqueue_released_slip_item(
        self,
        slip_item_id: UUID,
        org_id: UUID,
        worker_id: UUID | None = None,
    ) -> PutAwayList:
        """Add a manager-released exception line to normal put-away.

        A receipt may already have a put-away list when one held line is later
        released.  Creating a second receipt list would break the one-slip
        handoff, so the released line is appended to the existing list.
        """
        from app.models.receiving_slip import ReceivingSlipItem

        slip_item = (
            self.db.query(ReceivingSlipItem)
            .filter(
                ReceivingSlipItem.id == slip_item_id,
                ReceivingSlipItem.organization_id == org_id,
            )
            .first()
        )
        if slip_item is None:
            raise NotFoundError(
                message="Receiving slip item not found",
                entity_type="ReceivingSlipItem",
                entity_id=str(slip_item_id),
            )
        if slip_item.flag != "ok" or slip_item.condition_code != "GOOD":
            raise StateError(
                message="Only a released GOOD receipt line can be queued for put-away",
                current_state=slip_item.flag,
                required_state=["ok"],
            )

        slip = self.db.get(ReceivingSlip, slip_item.slip_id)
        if slip is None:
            raise NotFoundError(
                message="Receiving slip not found",
                entity_type="ReceivingSlip",
                entity_id=str(slip_item.slip_id),
            )

        existing_list = (
            self.db.query(PutAwayList)
            .filter(
                PutAwayList.receiving_slip_id == slip.id,
                PutAwayList.reference_type == "receiving_slip",
            )
            .first()
        )
        if existing_list is None:
            # A receipt containing only held/quarantined stock may have been
            # marked complete without a normal list. Re-open it for the newly
            # released inventory, then use the standard list generator.
            slip.status = "pending_putaway"
            self.db.flush()
            return self.generate_from_slip(slip.id, org_id, worker_id)

        duplicate = (
            self.db.query(PutAwayListItem)
            .filter(
                PutAwayListItem.put_away_list_id == existing_list.id,
                PutAwayListItem.sku == slip_item.sku,
                PutAwayListItem.batch_number == slip_item.batch_number,
                PutAwayListItem.status.in_(["pending", "in_progress", "completed"]),
            )
            .first()
        )
        if duplicate is not None:
            return existing_list

        item = self._resolve_item_by_sku(slip_item.sku, org_id)
        if item is None:
            raise ValidationError(
                f"Released SKU '{slip_item.sku}' no longer resolves to an active item"
            )

        assignments = self._assign_bins(
            item_id=item.id,
            item_group_id=item.item_group_id,
            quantity=Decimal(str(slip_item.quantity)),
            warehouse_id=slip.warehouse_id,
            org_id=org_id,
        )
        if not assignments:
            raise ValidationError(
                f"No eligible pickable storage bin is available for released SKU '{slip_item.sku}'"
            )

        new_items: list[PutAwayListItem] = []
        for assignment in assignments:
            put_away_item = PutAwayListItem(
                organization_id=org_id,
                put_away_list_id=existing_list.id,
                item_id=item.id,
                sku=slip_item.sku,
                batch_number=slip_item.batch_number,
                quantity=assignment["quantity"],
                bin_location_id=assignment["bin_location_id"],
                sort_order=0,
                status="pending",
            )
            self.db.add(put_away_item)
            new_items.append(put_away_item)

        existing_list.status = "pending"
        existing_list.completed_at = None
        if worker_id is not None:
            existing_list.assigned_to = worker_id
        slip.status = "pending_putaway"
        self.db.flush()
        self._optimize_item_routing(new_items)
        self.db.commit()
        self.db.refresh(existing_list)
        return existing_list

    def complete_item(
        self,
        put_away_item_id: UUID,
        worker_id: UUID,
        org_id: UUID,
        bin_id_override: UUID | None = None,
    ) -> PutAwayListItem:
        """Complete a put-away item, updating bin stock and marking as COMPLETED.

        Triggers capacity rollup on completion. Updates receiving slip to
        PUTAWAY_COMPLETE when all items are done.

        Args:
            put_away_item_id: The put-away list item ID to complete.
            worker_id: The worker completing the item.
            org_id: Organization ID for scoping.
            bin_id_override: Optional bin location ID to use instead of the
                pre-assigned bin_location_id on the put-away item.

        Returns:
            The updated PutAwayListItem.

        Raises:
            NotFoundError: If put-away item is not found.
            StateError: If item is not in pending status.
            ValidationError: If bin_location_id is not assigned.

        Requirements: 8.5, 8.6, 18.1, 18.3
        """
        put_away_item = (
            self.db.query(PutAwayListItem)
            .filter(
                PutAwayListItem.id == put_away_item_id,
                PutAwayListItem.organization_id == org_id,
            )
            .first()
        )

        if put_away_item is None:
            raise NotFoundError(
                message="Put-away list item not found",
                entity_type="PutAwayListItem",
                entity_id=str(put_away_item_id),
            )

        if put_away_item.status != "pending":
            raise StateError(
                message="Put-away item must be in pending status to complete",
                current_state=put_away_item.status,
                required_state=["pending"],
            )

        # Use override bin if provided, otherwise fall back to pre-assigned bin
        target_bin_id = bin_id_override or put_away_item.bin_location_id
        if target_bin_id is None:
            raise ValidationError(
                "Cannot complete put-away item without an assigned bin location"
            )

        # If the worker chose a bin different from the pre-assigned one,
        # update the put-away item record to reflect the actual destination.
        if (
            bin_id_override is not None
            and bin_id_override != put_away_item.bin_location_id
        ):
            put_away_item.bin_location_id = bin_id_override

        # Approved receipts first exist in the non-pickable RECEIVING-STAGE.
        # Completing a put-away moves that stock into its final pickable bin;
        # legacy/direct flows without staged stock retain the prior add-stock
        # behavior.
        bin_stock = self._move_from_receiving_stage_or_add(
            put_away_item=put_away_item,
            target_bin_id=target_bin_id,
            org_id=org_id,
        )

        # If the put-away item carries a packaging_unit_id, propagate it to the
        # BinStockLevel row as metadata (Req 3.3).
        put_away_packaging_unit_id = getattr(put_away_item, "packaging_unit_id", None)
        if put_away_packaging_unit_id is not None:
            bin_stock.packaging_unit_id = put_away_packaging_unit_id
            self.db.flush()
            # Recompute capacity with the actual (case-pack) dimensions.
            BinCapacityService(self.db).refresh_bin(target_bin_id, org_id)

        # Mark item as completed
        put_away_item.status = "completed"
        put_away_item.completed_at = datetime.now(UTC)
        self.db.flush()

        # ── NEW: Update tracking records for this put-away ──
        self._update_tracking_on_putaway(
            put_away_item=put_away_item,
            target_bin_id=target_bin_id,
            worker_id=worker_id,
            org_id=org_id,
        )

        # Release any reservation the worker held on the destination bin so it
        # becomes immediately available to others (FR-CW lifecycle).
        self.reservation_service.release(
            bin_id=target_bin_id, worker_id=worker_id, org_id=org_id
        )

        # Check if all items in the put-away list are done
        self._check_and_update_list_completion(put_away_item.put_away_list_id)

        self.db.commit()
        self.db.refresh(put_away_item)
        return put_away_item

    def skip_item(
        self, put_away_item_id: UUID, reason: str, org_id: UUID
    ) -> PutAwayListItem:
        """Skip a put-away item with a reason.

        Args:
            put_away_item_id: The put-away list item ID to skip.
            reason: The reason for skipping.
            org_id: Organization ID for scoping.

        Returns:
            The updated PutAwayListItem.

        Raises:
            NotFoundError: If put-away item is not found.
            StateError: If item is not in pending status.
            ValidationError: If reason is empty.
        """
        if not reason or not reason.strip():
            raise ValidationError(
                "A reason must be provided when skipping a put-away item"
            )

        put_away_item = (
            self.db.query(PutAwayListItem)
            .filter(
                PutAwayListItem.id == put_away_item_id,
                PutAwayListItem.organization_id == org_id,
            )
            .first()
        )

        if put_away_item is None:
            raise NotFoundError(
                message="Put-away list item not found",
                entity_type="PutAwayListItem",
                entity_id=str(put_away_item_id),
            )

        if put_away_item.status != "pending":
            raise StateError(
                message="Put-away item must be in pending status to skip",
                current_state=put_away_item.status,
                required_state=["pending"],
            )

        # Mark item as skipped with reason
        put_away_item.status = "skipped"
        put_away_item.notes = reason
        self.db.flush()

        # Check if all items in the put-away list are done (completed or skipped)
        self._check_and_update_list_completion(put_away_item.put_away_list_id)

        self.db.commit()
        self.db.refresh(put_away_item)
        return put_away_item

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _resolve_item_by_sku(self, sku_value: str, org_id: UUID) -> Item | None:
        """Resolve an Item deterministically by item_code → sku → gtin.

        The same value can be one item's GTIN while also being another item's
        code or SKU, so the previous OR-filtered ``.first()`` could return an
        arbitrary match. Explicit priority makes the resolution stable.
        """
        for column in (Item.item_code, Item.sku, Item.gtin):
            item = (
                self.db.query(Item)
                .filter(column == sku_value, Item.organization_id == org_id)
                .first()
            )
            if item is not None:
                return item
        return None

    def _assign_bins(
        self,
        item_id: UUID,
        item_group_id: UUID | None,
        quantity: Decimal,
        warehouse_id: UUID,
        org_id: UUID,
    ) -> list[dict]:
        """Assign bins for an item respecting allocations and capacity.

        Allocation priority:
        1. Exclusive allocations for the item's group — only use those bins
        2. Preferred allocations for the item's group — try those first
        3. Unallocated bins — fall back if preferred bins insufficient

        Filters bins by: is_active=True, available_capacity >= needed quantity.
        Splits across bins if single bin insufficient.

        Args:
            item_id: The item to assign bins for.
            item_group_id: The item's group ID for allocation lookup.
            quantity: Total quantity to assign.
            warehouse_id: The warehouse to search bins in.
            org_id: Organization ID for scoping.

        Returns:
            List of dicts with bin_location_id and quantity.

        Requirements: 20.3, 20.4, 20.5, 20.6
        """
        assignments: list[dict] = []
        remaining_qty = quantity

        # Exclude bins actively reserved by workers so generated put-away tasks
        # do not collide with in-progress work (FR-CW-01).
        reserved_bin_ids = self.reservation_service.get_reserved_bin_ids(
            org_id=org_id, warehouse_id=warehouse_id
        )

        if item_group_id is not None:
            # Step 1: Check for exclusive allocations
            exclusive_allocations = (
                self.db.query(LocationAllocation)
                .filter(
                    LocationAllocation.organization_id == org_id,
                    LocationAllocation.item_group_id == item_group_id,
                    LocationAllocation.allocation_type == "exclusive",
                    LocationAllocation.is_active == True,  # noqa: E712
                )
                .join(
                    WarehouseLocation,
                    LocationAllocation.location_id == WarehouseLocation.id,
                )
                .filter(
                    WarehouseLocation.warehouse_id == warehouse_id,
                )
                .order_by(LocationAllocation.priority.desc())
                .all()
            )

            if exclusive_allocations:
                # Only use exclusively allocated bins
                exclusive_bins = self._get_bins_from_allocations(
                    exclusive_allocations, org_id
                )
                assignments, remaining_qty = self._fill_bins(
                    exclusive_bins, remaining_qty, org_id, reserved_bin_ids
                )
                # For exclusive allocations, we don't fall back to other bins
                if remaining_qty > 0:
                    # If we can't fit everything in exclusive bins, still return
                    # what we have — the remaining will be unassigned
                    pass
                return assignments

            # Step 2: Check for preferred allocations
            preferred_allocations = (
                self.db.query(LocationAllocation)
                .filter(
                    LocationAllocation.organization_id == org_id,
                    LocationAllocation.item_group_id == item_group_id,
                    LocationAllocation.allocation_type == "preferred",
                    LocationAllocation.is_active == True,  # noqa: E712
                )
                .join(
                    WarehouseLocation,
                    LocationAllocation.location_id == WarehouseLocation.id,
                )
                .filter(
                    WarehouseLocation.warehouse_id == warehouse_id,
                )
                .order_by(LocationAllocation.priority.desc())
                .all()
            )

            if preferred_allocations:
                preferred_bins = self._get_bins_from_allocations(
                    preferred_allocations, org_id
                )
                assignments, remaining_qty = self._fill_bins(
                    preferred_bins, remaining_qty, org_id, reserved_bin_ids
                )

        # Step 3: Fall back to unallocated bins if still remaining
        if remaining_qty > 0:
            unallocated_bins = self._get_unallocated_bins(warehouse_id, org_id)
            additional_assignments, remaining_qty = self._fill_bins(
                unallocated_bins, remaining_qty, org_id, reserved_bin_ids
            )
            assignments.extend(additional_assignments)

        return assignments

    def _get_bins_from_allocations(
        self, allocations: list[LocationAllocation], org_id: UUID
    ) -> list[WarehouseLocation]:
        """Get active bin locations from allocation records.

        Allocations can point to bins, levels, bays, etc. We need to resolve
        down to actual bin locations.
        """
        bins: list[WarehouseLocation] = []

        for allocation in allocations:
            location = (
                self.db.query(WarehouseLocation)
                .filter(
                    WarehouseLocation.id == allocation.location_id,
                    WarehouseLocation.is_active == True,  # noqa: E712
                    WarehouseLocation.is_pickable == True,  # noqa: E712
                )
                .first()
            )

            if location is None:
                continue

            if location.location_type == "bin":
                bins.append(location)
            else:
                # Get all descendant bins
                descendant_bins = self._get_descendant_bins(location.id)
                bins.extend(descendant_bins)

        return bins

    def _get_descendant_bins(self, location_id: UUID) -> list[WarehouseLocation]:
        """Get all active descendant bin locations using BFS."""
        bins: list[WarehouseLocation] = []
        queue = [location_id]

        while queue:
            current_id = queue.pop(0)
            children = (
                self.db.query(WarehouseLocation)
                .filter(
                    WarehouseLocation.parent_location_id == current_id,
                    WarehouseLocation.is_active == True,  # noqa: E712
                    WarehouseLocation.is_pickable == True,  # noqa: E712
                )
                .all()
            )

            for child in children:
                if child.location_type == "bin":
                    bins.append(child)
                else:
                    queue.append(child.id)

        return bins

    def _get_unallocated_bins(
        self, warehouse_id: UUID, org_id: UUID
    ) -> list[WarehouseLocation]:
        """Get active bins that have no exclusive allocation.

        Returns bins in the warehouse that are not exclusively allocated
        to any item group.
        """
        # Get all bin IDs that have an active exclusive allocation
        exclusively_allocated_location_ids = (
            self.db.query(LocationAllocation.location_id)
            .filter(
                LocationAllocation.organization_id == org_id,
                LocationAllocation.allocation_type == "exclusive",
                LocationAllocation.is_active == True,  # noqa: E712
            )
            .subquery()
        )

        # Get all active bins in the warehouse that are NOT exclusively allocated
        # We need to check both direct bin allocations and ancestor allocations
        bins = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
                WarehouseLocation.location_type == "bin",
                WarehouseLocation.is_active == True,  # noqa: E712
                WarehouseLocation.is_pickable == True,  # noqa: E712
                ~WarehouseLocation.id.in_(exclusively_allocated_location_ids),
            )
            .all()
        )

        return bins

    def _fill_bins(
        self,
        bins: list[WarehouseLocation],
        quantity: Decimal,
        org_id: UUID,
        reserved_bin_ids: set[UUID] | None = None,
    ) -> tuple[list[dict], Decimal]:
        """Fill bins with the given quantity, respecting capacity.

        Splits across bins if a single bin is insufficient. Bins in
        ``reserved_bin_ids`` are skipped to avoid worker contention.

        Args:
            bins: List of candidate bin locations.
            quantity: Remaining quantity to assign.
            org_id: Organization ID.
            reserved_bin_ids: Bin ids currently reserved by workers.

        Returns:
            Tuple of (assignments list, remaining quantity).
        """
        assignments: list[dict] = []
        remaining = quantity
        reserved = reserved_bin_ids or set()

        for bin_loc in bins:
            if remaining <= 0:
                break

            if bin_loc.id in reserved:
                continue

            # Calculate available capacity for this bin
            available = self._get_bin_available_capacity(bin_loc)

            if available <= 0:
                continue

            # Assign as much as possible to this bin
            assign_qty = min(remaining, available)
            assignments.append(
                {
                    "bin_location_id": bin_loc.id,
                    "quantity": assign_qty,
                }
            )
            remaining -= assign_qty

        return assignments, remaining

    def _get_bin_available_capacity(self, bin_loc: WarehouseLocation) -> Decimal:
        """Get the available capacity of a bin location."""
        bin_capacity = Decimal(str(bin_loc.capacity or 0))

        # Get current stock in the bin
        current_stock = (
            self.db.query(
                func.coalesce(func.sum(BinStockLevel.quantity_on_hand), Decimal("0"))
            )
            .filter(BinStockLevel.bin_location_id == bin_loc.id)
            .scalar()
        ) or Decimal("0")

        # Subtract quantities already promised to pending put-away items so a
        # batch of assignments cannot over-allocate the same bin.
        pending_put_away = (
            self.db.query(
                func.coalesce(func.sum(PutAwayListItem.quantity), Decimal("0"))
            )
            .filter(
                PutAwayListItem.bin_location_id == bin_loc.id,
                PutAwayListItem.status.in_(["pending", "in_progress"]),
            )
            .scalar()
        ) or Decimal("0")

        return (
            bin_capacity - Decimal(str(current_stock)) - Decimal(str(pending_put_away))
        )

    def _optimize_item_routing(self, put_away_items: list[PutAwayListItem]) -> None:
        """Optimize the routing order for put-away items using the RoutingOptimizer.

        Groups items by aisle and sorts by optimal traversal order.

        Requirements: 8.3, 8.4
        """
        if not put_away_items:
            return

        # Build BinLocation objects for items that have assigned bins
        items_with_bins = [
            item for item in put_away_items if item.bin_location_id is not None
        ]

        if not items_with_bins:
            return

        # Load bin location data for routing
        bin_locations: list[BinLocation] = []
        item_map: dict = {}  # Map BinLocation index to PutAwayListItem

        for _i, item in enumerate(items_with_bins):
            bin_loc = (
                self.db.query(WarehouseLocation)
                .filter(WarehouseLocation.id == item.bin_location_id)
                .first()
            )
            if bin_loc is None:
                continue

            bl = BinLocation(
                id=item.id,
                full_path=bin_loc.full_path or "",
                position_x=float(bin_loc.position_x or 0),
                position_y=float(bin_loc.position_y or 0),
            )
            bin_locations.append(bl)
            item_map[item.id] = item

        if not bin_locations:
            return

        # Optimize the route
        optimized = self.routing_optimizer.optimize(bin_locations)

        # Apply sort_order back to put-away items
        for opt_loc in optimized:
            if opt_loc.id in item_map:
                item_map[opt_loc.id].sort_order = opt_loc.sort_order

        self.db.flush()

    def _update_tracking_on_putaway(
        self,
        put_away_item,
        target_bin_id: UUID,
        worker_id: UUID,
        org_id: UUID,
    ) -> None:
        """Update scanned_item_tracking records when put-away completes."""
        import logging

        logger = logging.getLogger(__name__)

        from app.models.scanned_item_tracking import ScannedItemTracking

        put_away_list = put_away_item.put_away_list
        if not put_away_list or not put_away_list.receiving_slip_id:
            return

        trackings = (
            self.db.query(ScannedItemTracking)
            .filter(
                ScannedItemTracking.receiving_slip_id
                == put_away_list.receiving_slip_id,
                ScannedItemTracking.item_id == put_away_item.item_id,
                ScannedItemTracking.batch_number == put_away_item.batch_number,
                ScannedItemTracking.putaway_status == "pending",
            )
            .all()
        )

        if not trackings:
            return

        now = datetime.now(UTC)
        for t in trackings:
            t.putaway_status = "completed"
            t.bin_location_id = target_bin_id
            t.putaway_at = now
            t.putaway_by = worker_id

            # Stock for this item/batch was already added to the target bin by
            # complete_item(); mark the tracking rows as entered so the
            # dual-axis state machine stays consistent (avoid double-counting).
            if t.receiving_status == "approved" and not t.stock_entered:
                t.stock_entered = True
                t.stock_entered_at = now
            t.stock_location_id = target_bin_id

        self.db.flush()
        logger.info(
            "Tracking: %d records updated for put-away item %s",
            len(trackings),
            put_away_item.id,
        )

    def _move_from_receiving_stage_or_add(
        self,
        *,
        put_away_item: PutAwayListItem,
        target_bin_id: UUID,
        org_id: UUID,
    ) -> BinStockLevel:
        """Move receipt-stage stock into storage, with legacy-flow fallback."""
        put_away_list = put_away_item.put_away_list
        if put_away_list and put_away_list.receiving_slip_id:
            stage = (
                self.db.query(WarehouseLocation)
                .filter(
                    WarehouseLocation.warehouse_id == put_away_list.warehouse_id,
                    WarehouseLocation.organization_id == org_id,
                    WarehouseLocation.code == "RECEIVING-STAGE",
                )
                .first()
            )
            if stage is not None:
                staged_stock = (
                    self.db.query(BinStockLevel)
                    .filter(
                        BinStockLevel.bin_location_id == stage.id,
                        BinStockLevel.item_id == put_away_item.item_id,
                        BinStockLevel.organization_id == org_id,
                        BinStockLevel.batch_number == put_away_item.batch_number,
                    )
                    .first()
                )
                if staged_stock is not None:
                    required = Decimal(str(put_away_item.quantity))
                    available = Decimal(str(staged_stock.quantity_on_hand or 0))
                    if available < required:
                        raise StateError(
                            message=(
                                f"RECEIVING-STAGE has {available} available for "
                                f"{put_away_item.sku} / batch {put_away_item.batch_number}; "
                                f"cannot put away {required}"
                            ),
                            current_state="insufficient_receiving_stage_stock",
                            required_state=["staged_quantity_available"],
                        )
                    return self.bin_stock_service.transfer_stock(
                        from_bin_id=stage.id,
                        to_bin_id=target_bin_id,
                        item_id=put_away_item.item_id,
                        quantity=required,
                        org_id=org_id,
                        batch_number=put_away_item.batch_number,
                    )

        return self.bin_stock_service.add_stock(
            bin_id=target_bin_id,
            item_id=put_away_item.item_id,
            quantity=Decimal(str(put_away_item.quantity)),
            org_id=org_id,
            batch_number=put_away_item.batch_number,
        )

    def _check_and_update_list_completion(self, put_away_list_id: UUID) -> None:
        """Check if all items in a put-away list are done and update statuses.

        When all items are completed or skipped:
        - Mark the put-away list as completed
        - Update the receiving slip to PUTAWAY_COMPLETE

        Requirements: 8.6
        """
        put_away_list = (
            self.db.query(PutAwayList)
            .filter(PutAwayList.id == put_away_list_id)
            .first()
        )

        if put_away_list is None:
            return

        # Count pending items
        pending_count = (
            self.db.query(func.count(PutAwayListItem.id))
            .filter(
                PutAwayListItem.put_away_list_id == put_away_list_id,
                PutAwayListItem.status == "pending",
            )
            .scalar()
        ) or 0

        if pending_count == 0:
            # All items are done (completed or skipped)
            put_away_list.status = "completed"
            put_away_list.completed_at = datetime.now(UTC)
            self.db.flush()

            # Update receiving slip to PUTAWAY_COMPLETE
            if put_away_list.receiving_slip_id:
                slip = (
                    self.db.query(ReceivingSlip)
                    .filter(ReceivingSlip.id == put_away_list.receiving_slip_id)
                    .first()
                )
                if slip and slip.status == "pending_putaway":
                    slip.status = "putaway_complete"
                    self.db.flush()
                    # Put-away is the terminal receiving step — refresh ASN
                    # delivered quantities and delivery status so the ASN
                    # closes out as delivered / partially_delivered.
                    if slip.asn_order_id:
                        from app.services.inbound_service import InboundService

                        InboundService(self.db)._sync_asn_delivered_qty(
                            slip.asn_order_id, slip.organization_id
                        )
