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

    def generate_from_slip(
        self, slip_id: UUID, org_id: UUID, worker_id: UUID | None = None
    ) -> PutAwayList:
        """Generate a put-away list from an approved receiving slip.

        Assigns bins respecting allocations (exclusive first, then preferred,
        then unallocated) and capacity. Groups items by zone/aisle and sorts
        by optimal traversal order. Creates a worker task via TaskService
        if a worker_id is provided.

        Args:
            slip_id: The receiving slip ID to generate put-away from.
            org_id: Organization ID for scoping.
            worker_id: Optional worker ID to assign the put-away task to.

        Returns:
            The created PutAwayList with items assigned to bins.

        Raises:
            NotFoundError: If receiving slip is not found.
            StateError: If slip is not in pending_putaway status.

        Requirements: 8.1, 8.2, 8.3, 8.4, 20.3, 20.4, 20.5, 20.6
        """
        # Validate the receiving slip
        slip = (
            self.db.query(ReceivingSlip)
            .filter(
                ReceivingSlip.id == slip_id,
                ReceivingSlip.organization_id == org_id,
            )
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

        # Generate unique put-away list number
        from app.services.document_numbering_service import DocumentNumberingService

        put_away_number = DocumentNumberingService(self.db).get_next_number(
            org_id, "put_away_list"
        )

        # Create the put-away list
        put_away_list = PutAwayList(
            organization_id=org_id,
            warehouse_id=slip.warehouse_id,
            put_away_list_no=put_away_number,
            status="pending",
            reference_type="receiving_slip",
            reference_id=slip_id,
            receiving_slip_id=slip_id,
        )
        self.db.add(put_away_list)
        self.db.flush()

        # Process each receiving slip item and assign bins
        put_away_items = []
        skipped_damaged: list[str] = []
        skipped_rejected: list[str] = []
        skipped_unresolved: list[str] = []
        for slip_item in slip.items:
            # Skip items flagged as damaged or rejected
            if slip_item.flag in ("damaged", "rejected"):
                skipped = (
                    skipped_damaged if slip_item.flag == "damaged" else skipped_rejected
                )
                skipped.append(
                    f"{slip_item.sku} (batch: {slip_item.batch_number}, qty: {slip_item.quantity})"
                )
                continue

            # Resolve item from SKU — match by item_code or sku field.
            # QR-product-linked items store the GTIN in Item.sku while
            # manually-created items are typically matched by item_code.
            item = (
                self.db.query(Item)
                .filter(
                    (Item.item_code == slip_item.sku) | (Item.sku == slip_item.sku),
                    Item.organization_id == org_id,
                )
                .first()
            )

            if item is None:
                # If item not found by code, skip this item
                skipped_unresolved.append(
                    f"{slip_item.sku} (batch: {slip_item.batch_number})"
                )
                continue

            quantity = Decimal(str(slip_item.quantity))
            item_group_id = item.item_group_id

            # Assign bins for this item
            bin_assignments = self._assign_bins(
                item_id=item.id,
                item_group_id=item_group_id,
                quantity=quantity,
                warehouse_id=slip.warehouse_id,
                org_id=org_id,
            )

            # Create put-away list items from bin assignments
            for assignment in bin_assignments:
                put_away_item = PutAwayListItem(
                    organization_id=org_id,
                    put_away_list_id=put_away_list.id,
                    item_id=item.id,
                    sku=slip_item.sku,
                    batch_number=slip_item.batch_number,
                    quantity=assignment["quantity"],
                    bin_location_id=assignment["bin_location_id"],
                    sort_order=0,  # Will be set by routing optimizer
                    status="pending",
                )
                self.db.add(put_away_item)
                put_away_items.append(put_away_item)

        # Build warnings for skipped items (stored in remarks as JSON)
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
        if skipped_unresolved:
            warnings_parts.append(
                f"Skipped {len(skipped_unresolved)} item(s) with unknown SKU (no matching Item found): "
                + "; ".join(skipped_unresolved)
            )
        if warnings_parts:
            put_away_list.remarks = json.dumps({"warnings": warnings_parts})

        self.db.flush()

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

        # Add stock to the target bin using BinStockService
        bin_stock = self.bin_stock_service.add_stock(
            bin_id=target_bin_id,
            item_id=put_away_item.item_id,
            quantity=Decimal(str(put_away_item.quantity)),
            org_id=org_id,
            batch_number=put_away_item.batch_number,
        )

        # If the put-away item carries a packaging_unit_id, propagate it to the
        # BinStockLevel row as metadata (Req 3.3).
        put_away_packaging_unit_id = getattr(put_away_item, "packaging_unit_id", None)
        if put_away_packaging_unit_id is not None:
            bin_stock.packaging_unit_id = put_away_packaging_unit_id
            self.db.flush()

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

        return bin_capacity - Decimal(str(current_stock))

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

            # Enter stock if receiving is also approved (no double entry — stock_entered flag guards)
            if t.receiving_status == "approved" and not t.stock_entered:
                from app.services.bin_stock_service import BinStockService

                BinStockService.add_stock(
                    bin_location_id=t.bin_location_id,
                    item_id=t.item_id,
                    quantity=t.quantity,
                    batch_number=t.batch_number,
                )
                t.stock_entered = True
                t.stock_entered_at = now

        self.db.flush()
        logger.info(
            "Tracking: %d records updated for put-away item %s",
            len(trackings),
            put_away_item.id,
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
