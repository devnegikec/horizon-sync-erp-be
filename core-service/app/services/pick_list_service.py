"""Pick list service.

Handles CRUD operations for pick lists and SAP invoice-triggered outbound workflow.

Provides:
- Standard CRUD (create, get, list, update, delete)
- create_from_invoice: Parse SAP invoice payload, create pick list with items
- resolve_bin_locations: FIFO bin resolution with routing optimization
- record_pick_scan: QR scan-based pick fulfillment with stock decrement
- complete_pick_list: Mark pick list as completed when all items fully picked
- cancel_pick_list: Cancel pick list and release reserved stock

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 11.1, 11.2, 11.5
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationError
from app.models.base import PickListStatus
from app.models.bin_stock_level import BinStockLevel
from app.models.pick_list import PickList, PickListItem
from app.models.qr_scan_event import QRScanEvent
from app.models.warehouse_location import WarehouseLocation
from app.repositories.pick_list_repository import PickListRepository
from app.services.qr_decoder import decode_qr_payload
from app.services.routing_optimizer import BinLocation, RoutingOptimizer


@dataclass
class SAPInvoiceItem:
    """Represents a single line item from a SAP invoice payload."""

    item_id: UUID
    sku: str
    quantity: Decimal
    uom: str


@dataclass
class SAPInvoicePayload:
    """Represents the parsed SAP invoice payload."""

    invoice_reference: str
    warehouse_id: UUID
    items: list[SAPInvoiceItem]


class PickListService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PickListRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = {k: v for k, v in data.items() if k != "items"}
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        # Auto-generate pick_list_no if not provided
        if not payload.get("pick_list_no"):
            from app.services.document_numbering_service import DocumentNumberingService

            payload["pick_list_no"] = DocumentNumberingService(self.db).get_next_number(
                organization_id, "pick_list"
            )
        if payload.get("status"):
            payload["status"] = PickListStatus(payload["status"])
        items = data.get("items") or []
        item_list = [dict(it) for it in items]
        pl = self.repo.create(payload, item_list)
        return self._to_response(pl)

    def get_by_id(self, pick_list_id: UUID, organization_id: UUID) -> dict:
        pl = self.repo.get_by_id(pick_list_id, organization_id)
        if not pl:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")
        return self._to_response_enriched(pl)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        warehouse_id: UUID | None = None,
        status: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_pick_lists(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            warehouse_id=warehouse_id,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return [self._to_list_item(x) for x in items], pagination

    def update(
        self, pick_list_id: UUID, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        pl = self.repo.get_by_id(pick_list_id, organization_id)
        if not pl:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")
        payload = {k: v for k, v in data.items() if v is not None}
        if payload.get("status"):
            payload["status"] = PickListStatus(payload["status"])
        payload["updated_by"] = user_id
        self.repo.update(pl, payload)
        self.db.refresh(pl)
        return self._to_response(pl)

    def delete(self, pick_list_id: UUID, organization_id: UUID) -> None:
        pl = self.repo.get_by_id(pick_list_id, organization_id)
        if not pl:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")
        self.repo.delete(pl)

    # ------------------------------------------------------------------
    # SAP INVOICE-TRIGGERED OUTBOUND WORKFLOW
    # ------------------------------------------------------------------

    def create_from_invoice(
        self,
        invoice_data: SAPInvoicePayload,
        org_id: UUID,
        worker_id: UUID | None = None,
    ) -> PickList:
        """Create a pick list from a SAP invoice payload.

        Parses the invoice payload, creates a pick list with status DRAFT (OPEN),
        populates items from invoice lines, resolves bin locations using FIFO logic,
        optimizes the route, and creates a worker task.

        Args:
            invoice_data: Parsed SAP invoice payload with invoice_reference,
                          warehouse_id, and items list.
            org_id: Organization ID for scoping.
            worker_id: Optional worker UUID to assign the pick task to.

        Returns:
            The created PickList with items populated, bin locations resolved,
            and sort_order set.

        Raises:
            ValidationError: If invoice data is invalid (no items, missing fields).

        Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
        """
        if not invoice_data.items:
            raise ValidationError("Invoice must contain at least one line item")

        if not invoice_data.invoice_reference:
            raise ValidationError("Invoice reference is required")

        if not invoice_data.warehouse_id:
            raise ValidationError("Warehouse ID is required")

        # Generate pick list number
        from app.services.document_numbering_service import DocumentNumberingService

        pick_list_no = DocumentNumberingService(self.db).get_next_number(
            org_id, "pick_list"
        )

        # Create the pick list
        pick_list = PickList(
            organization_id=org_id,
            pick_list_no=pick_list_no,
            warehouse_id=invoice_data.warehouse_id,
            status=PickListStatus.DRAFT,
            pick_date=datetime.now(UTC),
            reference_type="sap_invoice",
            invoice_reference=invoice_data.invoice_reference,
            invoice_data={
                "invoice_reference": invoice_data.invoice_reference,
                "warehouse_id": str(invoice_data.warehouse_id),
                "items": [
                    {
                        "item_id": str(item.item_id),
                        "sku": item.sku,
                        "quantity": str(item.quantity),
                        "uom": item.uom,
                    }
                    for item in invoice_data.items
                ],
            },
        )
        self.db.add(pick_list)
        self.db.flush()

        # Create pick list items from invoice lines
        for item in invoice_data.items:
            pick_list_item = PickListItem(
                organization_id=org_id,
                pick_list_id=pick_list.id,
                item_id=item.item_id,
                warehouse_id=invoice_data.warehouse_id,
                qty=item.quantity,
                picked_qty=Decimal("0"),
                uom=item.uom,
                sort_order=0,
            )
            self.db.add(pick_list_item)

        self.db.commit()
        self.db.refresh(pick_list)

        # Resolve bin locations using FIFO and optimize route (Req 9.3, 9.4)
        pick_list = self.resolve_bin_locations(pick_list.id, org_id)

        # Create a worker task for the pick list if worker_id is provided
        if worker_id:
            from app.services.task_service import TaskService

            task_service = TaskService(self.db)
            task_service.create_task(
                task_type="pick",
                worker_id=worker_id,
                reference_id=pick_list.id,
                org_id=org_id,
            )

        return pick_list

    def resolve_bin_locations(self, pick_list_id: UUID, org_id: UUID) -> PickList:
        """Resolve bin locations for pick list items using FIFO logic.

        For each pick list item:
        1. Query bin_stock_levels WHERE item_id = X AND quantity_on_hand > 0
        2. ORDER BY created_at ASC (oldest stock first = FIFO)
        3. Allocate from oldest bins, splitting across bins if needed
        4. Pass resolved locations to RoutingOptimizer for sort ordering

        Args:
            pick_list_id: The pick list to resolve bins for.
            org_id: Organization ID for scoping.

        Returns:
            The updated PickList with bin_location_id and sort_order set on items.

        Raises:
            ResourceNotFoundException: If pick list not found.

        Requirements: 9.3, 9.4
        """
        pick_list = self.repo.get_by_id(pick_list_id, org_id)
        if not pick_list:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")

        # Collect all resolved items (may split one item across multiple bins)
        resolved_items: list[PickListItem] = []
        items_to_remove: list[PickListItem] = []

        for item in list(pick_list.items):
            remaining_qty = Decimal(str(item.qty))

            # Query bin stock levels for this item using FIFO (oldest first)
            bin_stocks = (
                self.db.query(BinStockLevel)
                .filter(
                    BinStockLevel.item_id == item.item_id,
                    BinStockLevel.organization_id == org_id,
                    BinStockLevel.quantity_on_hand > 0,
                )
                .order_by(BinStockLevel.created_at.asc())
                .all()
            )

            if not bin_stocks:
                # No stock available; keep item without bin assignment
                resolved_items.append(item)
                continue

            # Track whether we need to split across bins
            allocations: list[tuple[UUID, Decimal]] = []

            for bin_stock in bin_stocks:
                if remaining_qty <= 0:
                    break

                available = Decimal(str(bin_stock.quantity_on_hand))
                allocate_qty = min(remaining_qty, available)
                allocations.append((bin_stock.bin_location_id, allocate_qty))
                remaining_qty -= allocate_qty

            if len(allocations) == 0:
                # No allocations possible
                resolved_items.append(item)
            elif len(allocations) == 1:
                # Single bin can fulfill the entire quantity
                bin_location_id, _ = allocations[0]
                item.bin_location_id = bin_location_id
                resolved_items.append(item)
            else:
                # Need to split across multiple bins
                items_to_remove.append(item)

                for bin_location_id, alloc_qty in allocations:
                    split_item = PickListItem(
                        organization_id=org_id,
                        pick_list_id=pick_list.id,
                        item_id=item.item_id,
                        warehouse_id=item.warehouse_id,
                        qty=alloc_qty,
                        picked_qty=Decimal("0"),
                        uom=item.uom,
                        batch_no=item.batch_no,
                        bin_location_id=bin_location_id,
                        sort_order=0,
                    )
                    self.db.add(split_item)
                    resolved_items.append(split_item)

        # Remove original items that were split
        for item in items_to_remove:
            self.db.delete(item)

        self.db.flush()

        # Refresh to get the new items
        self.db.refresh(pick_list)

        # Apply routing optimization to all items with bin locations
        self._apply_routing_optimization(pick_list)

        self.db.commit()
        self.db.refresh(pick_list)
        return pick_list

    # ------------------------------------------------------------------
    # PICK SCAN RECORDING AND STATUS TRANSITIONS
    # ------------------------------------------------------------------

    def record_pick_scan(  # noqa: C901
        self,
        pick_list_id: UUID,
        qr_data: str,
        worker_id: UUID,
        org_id: UUID,
    ) -> dict:
        """Record a pick scan against a pick list.

        Decodes the QR payload, matches the SKU against pick list items,
        increments picked_qty, decrements bin stock, and transitions the
        pick list to IN_PROGRESS on the first scan.

        Args:
            pick_list_id: The pick list to record the scan against.
            qr_data: Raw QR payload JSON string.
            worker_id: The worker performing the scan.
            org_id: Organization ID for scoping.

        Returns:
            Dict with scan result details.

        Raises:
            ResourceNotFoundException: If pick list not found.
            ValidationError: If pick list is not in a scannable state,
                item not on pick list, or over-picking would occur.

        Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 11.2
        """
        pick_list = self.repo.get_by_id(pick_list_id, org_id)
        if not pick_list:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")

        # Only allow scanning on DRAFT (OPEN) or IN_PROGRESS pick lists
        if pick_list.status not in (PickListStatus.DRAFT, PickListStatus.IN_PROGRESS):
            raise ValidationError(
                f"Cannot scan items on pick list with status '{pick_list.status.value}'. "
                f"Pick list must be in 'draft' or 'in_progress' status."
            )

        # Decode QR payload
        payload = decode_qr_payload(qr_data)

        # Find matching pick list item by SKU (item_code)
        from app.models.item import Item

        item = (
            self.db.query(Item)
            .filter(
                Item.item_code == payload.sku,
                Item.organization_id == org_id,
            )
            .first()
        )

        if not item:
            raise ValidationError(
                f"Item with SKU '{payload.sku}' not found in organization"
            )

        # Find a pick list item that matches this item and still needs picking
        matching_pick_item = None
        for pick_item in pick_list.items:
            if pick_item.item_id == item.id:
                remaining = Decimal(str(pick_item.qty)) - Decimal(
                    str(pick_item.picked_qty or 0)
                )
                if remaining > 0:
                    matching_pick_item = pick_item
                    break

        if matching_pick_item is None:
            raise ValidationError(
                f"Item '{payload.sku}' is not on the pick list or has already been fully picked"
            )

        # Check for over-picking
        scanned_qty = Decimal(str(payload.qty))
        current_picked = Decimal(str(matching_pick_item.picked_qty or 0))
        required_qty = Decimal(str(matching_pick_item.qty))
        new_picked = current_picked + scanned_qty

        if new_picked > required_qty:
            raise ValidationError(
                f"Over-picking: scanning {payload.qty} would result in "
                f"{new_picked} picked, but only {required_qty} required "
                f"for item '{payload.sku}'"
            )

        # Increment picked_qty
        matching_pick_item.picked_qty = new_picked

        # Decrement bin stock if bin_location_id is set
        if matching_pick_item.bin_location_id:
            from app.services.bin_stock_service import BinStockService

            bin_stock_service = BinStockService(self.db)
            bin_stock_service.remove_stock(
                bin_id=matching_pick_item.bin_location_id,
                item_id=item.id,
                quantity=scanned_qty,
                org_id=org_id,
                batch_number=payload.batch,
            )

        # Transition to IN_PROGRESS on first scan
        if pick_list.status == PickListStatus.DRAFT:
            pick_list.status = PickListStatus.IN_PROGRESS

        # Record scan event in qr_scan_events
        scan_event = QRScanEvent(
            organization_id=org_id,
            serial_number=payload.id,
            scan_timestamp=datetime.now(UTC),
            extra_data={
                "scan_context": "pick",
                "pick_list_id": str(pick_list_id),
                "worker_id": str(worker_id),
                "pick_list_item_id": str(matching_pick_item.id),
                "decoded_payload": {
                    "id": payload.id,
                    "sku": payload.sku,
                    "qty": payload.qty,
                    "batch": payload.batch,
                },
            },
        )
        self.db.add(scan_event)

        self.db.commit()
        self.db.refresh(matching_pick_item)
        self.db.refresh(pick_list)

        return {
            "pick_list_id": str(pick_list_id),
            "pick_list_status": pick_list.status.value,
            "pick_list_item_id": str(matching_pick_item.id),
            "item_id": str(item.id),
            "sku": payload.sku,
            "scanned_qty": payload.qty,
            "picked_qty": float(matching_pick_item.picked_qty),
            "required_qty": float(matching_pick_item.qty),
            "remaining_qty": float(required_qty - new_picked),
            "batch": payload.batch,
        }

    def complete_pick_list(self, pick_list_id: UUID, org_id: UUID) -> PickList:
        """Mark a pick list as COMPLETED.

        Validates that all items have been fully picked before allowing
        completion.

        Args:
            pick_list_id: The pick list to complete.
            org_id: Organization ID for scoping.

        Returns:
            The updated PickList.

        Raises:
            ResourceNotFoundException: If pick list not found.
            ValidationError: If not all items are fully picked or
                pick list is not in a completable state.

        Requirements: 10.6, 10.7, 11.1
        """
        pick_list = self.repo.get_by_id(pick_list_id, org_id)
        if not pick_list:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")

        if pick_list.status not in (PickListStatus.DRAFT, PickListStatus.IN_PROGRESS):
            raise ValidationError(
                f"Cannot complete pick list with status '{pick_list.status.value}'. "
                f"Pick list must be in 'draft' or 'in_progress' status."
            )

        # Validate all items are fully picked
        for item in pick_list.items:
            picked = Decimal(str(item.picked_qty or 0))
            required = Decimal(str(item.qty))
            if picked < required:
                raise ValidationError(
                    f"Cannot complete pick list: item {item.id} has "
                    f"{picked} picked out of {required} required"
                )

        pick_list.status = PickListStatus.COMPLETED
        pick_list.completed_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(pick_list)
        return pick_list

    def cancel_pick_list(self, pick_list_id: UUID, org_id: UUID) -> PickList:
        """Cancel a pick list and release reserved stock.

        Increments bin stock back for any items that were already picked
        (reverses the stock decrement from pick scans).

        Args:
            pick_list_id: The pick list to cancel.
            org_id: Organization ID for scoping.

        Returns:
            The updated PickList.

        Raises:
            ResourceNotFoundException: If pick list not found.
            ValidationError: If pick list is already completed or cancelled.

        Requirements: 11.1, 11.5
        """
        pick_list = self.repo.get_by_id(pick_list_id, org_id)
        if not pick_list:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")

        if pick_list.status == PickListStatus.COMPLETED:
            raise ValidationError("Cannot cancel a completed pick list")

        if pick_list.status == PickListStatus.CANCELLED:
            raise ValidationError("Pick list is already cancelled")

        # Release reserved stock: add back any picked quantities to bin stock
        from app.services.bin_stock_service import BinStockService

        bin_stock_service = BinStockService(self.db)

        for item in pick_list.items:
            picked = Decimal(str(item.picked_qty or 0))
            if picked > 0 and item.bin_location_id:
                bin_stock_service.add_stock(
                    bin_id=item.bin_location_id,
                    item_id=item.item_id,
                    quantity=picked,
                    org_id=org_id,
                    batch_number=item.batch_no,
                )
            # Reset picked_qty
            item.picked_qty = Decimal("0")

        pick_list.status = PickListStatus.CANCELLED

        self.db.commit()
        self.db.refresh(pick_list)
        return pick_list

    def _apply_routing_optimization(self, pick_list: PickList) -> None:
        """Apply RoutingOptimizer to sort pick list items by optimal traversal order.

        Queries bin location positions and uses nearest-neighbor heuristic
        with aisle grouping to determine sort order.

        Requirements: 9.4
        """
        optimizer = RoutingOptimizer()

        # Collect items that have bin locations assigned
        items_with_bins: list[tuple[PickListItem, WarehouseLocation]] = []

        for item in pick_list.items:
            if item.bin_location_id:
                bin_location = (
                    self.db.query(WarehouseLocation)
                    .filter(WarehouseLocation.id == item.bin_location_id)
                    .first()
                )
                if bin_location:
                    items_with_bins.append((item, bin_location))

        if not items_with_bins:
            return

        # Build BinLocation objects for the optimizer
        bin_locations: list[BinLocation] = []
        item_map: dict[int, PickListItem] = {}  # map index to pick list item

        for idx, (item, location) in enumerate(items_with_bins):
            bin_loc = BinLocation(
                id=idx,
                full_path=location.full_path or "",
                position_x=float(location.position_x or 0),
                position_y=float(location.position_y or 0),
                sort_order=0,
            )
            bin_locations.append(bin_loc)
            item_map[idx] = item

        # Optimize the route
        optimized = optimizer.optimize(bin_locations)

        # Apply sort_order back to pick list items
        for bin_loc in optimized:
            item = item_map[bin_loc.id]
            item.sort_order = bin_loc.sort_order

        self.db.flush()

    @staticmethod
    def _to_response(pl) -> dict:
        return {
            "id": pl.id,
            "organization_id": pl.organization_id,
            "pick_list_no": pl.pick_list_no,
            "warehouse_id": pl.warehouse_id,
            "status": pl.status.value if pl.status else None,
            "pick_date": pl.pick_date,
            "reference_type": pl.reference_type,
            "reference_id": pl.reference_id,
            "remarks": pl.remarks,
            "completed_at": pl.completed_at,
            "created_by": pl.created_by,
            "updated_by": pl.updated_by,
            "created_at": pl.created_at,
            "updated_at": pl.updated_at,
            "items": [
                {
                    "id": item.id,
                    "organization_id": item.organization_id,
                    "pick_list_id": item.pick_list_id,
                    "item_id": item.item_id,
                    "warehouse_id": item.warehouse_id,
                    "qty": item.qty,
                    "picked_qty": item.picked_qty,
                    "uom": item.uom,
                    "batch_no": item.batch_no,
                    "sort_order": item.sort_order,
                    "created_at": item.created_at,
                }
                for item in pl.items
            ],
        }

    def _to_response_enriched(self, pl) -> dict:
        """Enhanced response with item, warehouse, and reference details"""
        from app.models.item import Item
        from app.models.sales_order import SalesOrder
        from app.models.warehouse import Warehouse

        # Get warehouse details for the pick list
        warehouse = None
        if pl.warehouse_id:
            warehouse = (
                self.db.query(Warehouse).filter(Warehouse.id == pl.warehouse_id).first()
            )

        # Get reference details (sales order)
        reference = None
        if pl.reference_type == "sales_order" and pl.reference_id:
            so = (
                self.db.query(SalesOrder)
                .filter(SalesOrder.id == pl.reference_id)
                .first()
            )
            if so:
                reference = {
                    "id": str(so.id),
                    "reference_type": "sales_order",
                    "name": so.sales_order_no,
                    "code": so.sales_order_no,
                }

        # Build enriched items with item and warehouse details
        enriched_items = []
        for item in pl.items:
            # Get item details
            item_obj = self.db.query(Item).filter(Item.id == item.item_id).first()

            # Get warehouse details for this item
            item_warehouse = (
                self.db.query(Warehouse)
                .filter(Warehouse.id == item.warehouse_id)
                .first()
            )

            enriched_item = {
                "id": item.id,
                "organization_id": item.organization_id,
                "item": {
                    "id": str(item_obj.id),
                    "name": item_obj.item_name,
                    "code": item_obj.item_code,
                }
                if item_obj
                else None,
                "warehouse": {
                    "id": str(item_warehouse.id),
                    "name": item_warehouse.name,
                    "code": item_warehouse.code,
                }
                if item_warehouse
                else None,
                "qty": item.qty,
                "picked_qty": item.picked_qty,
                "uom": item.uom,
                "batch_no": item.batch_no,
                "sort_order": item.sort_order,
                "created_at": item.created_at,
            }
            enriched_items.append(enriched_item)

        return {
            "id": pl.id,
            "organization_id": pl.organization_id,
            "pick_list_no": pl.pick_list_no,
            "warehouse_id": pl.warehouse_id,
            "warehouse": {
                "id": str(warehouse.id),
                "name": warehouse.name,
                "code": warehouse.code,
            }
            if warehouse
            else None,
            "status": pl.status.value if pl.status else None,
            "pick_date": pl.pick_date,
            "reference_type": pl.reference_type,
            "reference_id": pl.reference_id,
            "reference": reference,
            "remarks": pl.remarks,
            "completed_at": pl.completed_at,
            "created_by": pl.created_by,
            "updated_by": pl.updated_by,
            "created_at": pl.created_at,
            "updated_at": pl.updated_at,
            "items": enriched_items,
        }

    @staticmethod
    def _to_list_item(pl) -> dict:
        return {
            "id": pl.id,
            "organization_id": pl.organization_id,
            "pick_list_no": pl.pick_list_no,
            "warehouse_id": pl.warehouse_id,
            "status": pl.status.value if pl.status else None,
            "pick_date": pl.pick_date,
            "created_at": pl.created_at,
        }
