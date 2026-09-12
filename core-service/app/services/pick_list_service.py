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
from app.models.bin_stock_level import PICKABLE_INVENTORY_STATUSES, BinStockLevel
from app.models.item import Item
from app.models.pick_list import PickList, PickListItem
from app.models.qr_scan_event import QRScanEvent
from app.models.serial_no import SerialNo
from app.models.warehouse_location import LocationType, WarehouseLocation
from app.repositories.pick_list_repository import PickListRepository
from app.services.bin_reservation_service import BinReservationService
from app.services.qr_decoder import decode_qr_payload
from app.services.routing_optimizer import BinLocation, RoutingOptimizer

#: Serial statuses that must NOT be picked (WF-014 / EX-005 / EX-006 / ALT-003).
UNAVAILABLE_SERIAL_STATUSES: frozenset[str] = frozenset({"consumed", "blocked"})


@dataclass
class SAPInvoiceItem:
    """Represents a single line item from a SAP invoice payload."""

    item_id: UUID
    sku: str
    quantity: Decimal
    uom: str
    per_case_qty: Decimal | None = None
    case_qty: Decimal | None = None
    loose_qty: Decimal | None = None
    batch_no: str | None = None


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
        self.reservation_service = BinReservationService(db)

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
        aging_threshold = self._pick_config(organization_id).get_int(
            "aging_threshold_minutes"
        )
        return [
            self._to_list_item(x, aging_threshold) for x in items
        ], pagination

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
        assigned_to: UUID | None = None,
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
            assigned_to=assigned_to,
            invoice_data={
                "invoice_reference": invoice_data.invoice_reference,
                "warehouse_id": str(invoice_data.warehouse_id),
                "items": [
                    {
                        "item_id": str(item.item_id),
                        "sku": item.sku,
                        "quantity": str(item.quantity),
                        "uom": item.uom,
                        "per_case_qty": str(item.per_case_qty)
                        if item.per_case_qty is not None
                        else None,
                        "case_qty": str(item.case_qty)
                        if item.case_qty is not None
                        else None,
                        "loose_qty": str(item.loose_qty)
                        if item.loose_qty is not None
                        else None,
                        "batch_no": item.batch_no,
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
                per_case_qty=item.per_case_qty,
                case_qty=item.case_qty,
                loose_qty=item.loose_qty,
                batch_no=item.batch_no,
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

        # Bins actively reserved by workers must be skipped (FR-CW-01, FR-SL-02).
        reserved_bin_ids = self.reservation_service.get_reserved_bin_ids(org_id=org_id)

        for item in list(pick_list.items):
            remaining_qty = Decimal(str(item.qty))

            # Query bin stock levels for this item using FEFO then FIFO:
            # earliest expiry first (NULLs last), then oldest arrival.
            bin_stocks = (
                self.db.query(BinStockLevel)
                .join(
                    WarehouseLocation,
                    BinStockLevel.bin_location_id == WarehouseLocation.id,
                )
                .filter(
                    BinStockLevel.item_id == item.item_id,
                    BinStockLevel.organization_id == org_id,
                    BinStockLevel.quantity_on_hand > 0,
                    BinStockLevel.inventory_status.in_(PICKABLE_INVENTORY_STATUSES),
                    WarehouseLocation.is_pickable.is_(True),
                )
                .order_by(
                    BinStockLevel.expiry_date.asc().nullslast(),
                    BinStockLevel.created_at.asc(),
                )
                .all()
            )

            # Drop bins reserved by other workers.
            bin_stocks = [
                bs for bs in bin_stocks if bs.bin_location_id not in reserved_bin_ids
            ]

            if not bin_stocks:
                # No stock available; keep item without bin assignment
                resolved_items.append(item)
                continue

            # Track whether we need to split across bins
            allocations: list[tuple[UUID, Decimal, str | None]] = []

            for bin_stock in bin_stocks:
                if remaining_qty <= 0:
                    break

                available = Decimal(str(bin_stock.quantity_on_hand))
                allocate_qty = min(remaining_qty, available)
                allocations.append(
                    (bin_stock.bin_location_id, allocate_qty, bin_stock.batch_number)
                )
                remaining_qty -= allocate_qty

            if len(allocations) == 0:
                # No allocations possible
                resolved_items.append(item)
            elif len(allocations) == 1:
                # Single bin can fulfill the entire quantity
                bin_location_id, _, batch_number = allocations[0]
                item.bin_location_id = bin_location_id
                # Keep the packing-slip batch number; store the bin-stock serial(s)
                # separately so the batch column matches the uploaded PDF.
                item.serial_nos = [batch_number] if batch_number else None
                resolved_items.append(item)
            else:
                # Need to split across multiple bins
                items_to_remove.append(item)

                for split_idx, (bin_location_id, alloc_qty, batch_number) in enumerate(
                    allocations
                ):
                    split_item = PickListItem(
                        organization_id=org_id,
                        pick_list_id=pick_list.id,
                        item_id=item.item_id,
                        warehouse_id=item.warehouse_id,
                        qty=alloc_qty,
                        picked_qty=Decimal("0"),
                        uom=item.uom,
                        # Case/loose breakdown belongs to the line as a whole;
                        # carry it on the first split so it isn't duplicated.
                        per_case_qty=item.per_case_qty if split_idx == 0 else None,
                        case_qty=item.case_qty if split_idx == 0 else None,
                        loose_qty=item.loose_qty if split_idx == 0 else None,
                        batch_no=item.batch_no,
                        serial_nos=[batch_number] if batch_number else None,
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

    def validate_bin(
        self,
        org_id: UUID,
        pick_item: PickListItem,
        bin_location_id: UUID | None,
    ) -> None:
        """Enforce the wrong-bin hard stop (WF-012 / ALT-001 / EX-003).

        When ``pick.require_bin_scan`` is enabled (default ``true``), a picker
        must scan the source bin and it must match the bin assigned to the
        pick line. When the flag is off, legacy behaviour (no bin validation)
        is preserved.

        Raises:
            ValidationError: if a bin scan is required but missing, or the
                scanned bin does not match the line's assigned bin.
        """
        from app.services.pick_settings_service import PickConfigResolver

        require_bin_scan = PickConfigResolver.from_org(self.db, org_id).get_bool(
            "require_bin_scan"
        )
        if not require_bin_scan:
            return

        # No source bin assigned to the line — nothing to validate against.
        if pick_item.bin_location_id is None:
            return

        if bin_location_id is None:
            raise ValidationError(
                "Bin scan required: scan the source bin before scanning the item"
            )

        if bin_location_id != pick_item.bin_location_id:
            raise ValidationError(
                f"Wrong bin: expected bin {pick_item.bin_location_id}, "
                f"scanned bin {bin_location_id}"
            )

    def validate_serial(
        self,
        org_id: UUID,
        item: Item,
        serial_no: str | None,
    ) -> None:
        """Enforce serial validation (WF-014 / EX-005 / EX-006 / ALT-003).

        Policy is driven by ``pick.require_serial``:
        - ``never`` → skip.
        - ``per_item`` (default) → validate only serialized items
          (``item.has_serial_no``).
        - ``always`` → validate every scan.

        When enforced, the scanned serial must exist against ``serial_nos``
        for the scanned SKU (belongs-to-SKU) and must not be consumed or
        blocked. Raises ``ValidationError`` otherwise.
        """
        from app.services.pick_settings_service import PickConfigResolver

        policy = PickConfigResolver.from_org(self.db, org_id).get_enum(
            "require_serial"
        )
        if policy == "never":
            return
        if policy == "per_item" and not item.has_serial_no:
            return

        if not serial_no:
            raise ValidationError(
                f"Serial scan required for item '{item.item_code}'"
            )

        serial_row = (
            self.db.query(SerialNo)
            .filter(
                SerialNo.organization_id == org_id,
                SerialNo.serial_no == serial_no,
                SerialNo.item_id == item.id,
            )
            .first()
        )
        if serial_row is None:
            raise ValidationError(
                f"Serial '{serial_no}' is not valid for item '{item.item_code}'"
            )

        status = (serial_row.status or "").strip().lower()
        if status in UNAVAILABLE_SERIAL_STATUSES:
            raise ValidationError(
                f"Serial '{serial_no}' is {status} and cannot be picked"
            )

    def _pick_config(self, org_id: UUID):
        """Return a read-once snapshot of effective pick settings for an org."""
        from app.services.pick_settings_service import PickConfigResolver

        return PickConfigResolver.from_org(self.db, org_id)

    def validate_over_pick(
        self,
        org_id: UUID,
        required_qty: Decimal,
        new_picked: Decimal,
    ) -> None:
        """Enforce the over-pick tolerance (EX-021).

        A scan is blocked only when it exceeds the required quantity *plus*
        ``pick.over_pick_tolerance`` (default ``0`` → no over-pick allowed).
        """
        tolerance = Decimal(
            str(self._pick_config(org_id).get_numeric("over_pick_tolerance"))
        )
        if new_picked > required_qty + tolerance:
            raise ValidationError(
                f"Over-picking: scanning would result in {new_picked} picked, "
                f"but only {required_qty} required (tolerance {tolerance})"
            )

    def validate_short_pick(
        self,
        org_id: UUID,
        pick_item: PickListItem,
    ) -> Decimal | None:
        """Evaluate short-pick policy for a line (EX-002 / ALT-004).

        Returns the shortfall to record as an exception, or ``None`` when the
        line is fully picked. Raises ``ValidationError`` when short-picking is
        disabled (``pick.allow_short_pick``) or the shortfall exceeds
        ``pick.short_pick_approval_threshold`` (requires supervisor approval).
        """
        shortfall = Decimal(str(pick_item.qty)) - Decimal(
            str(pick_item.picked_qty or 0)
        )
        if shortfall <= 0:
            return None

        config = self._pick_config(org_id)
        if not config.get_bool("allow_short_pick"):
            raise ValidationError(
                f"Short-pick of {shortfall} on item {pick_item.id} is not allowed"
            )
        threshold = Decimal(
            str(config.get_numeric("short_pick_approval_threshold"))
        )
        if shortfall > threshold:
            raise ValidationError(
                f"Short-pick of {shortfall} on item {pick_item.id} exceeds the "
                f"approval threshold {threshold}"
            )
        return shortfall

    def _capture_short_pick_exception(
        self,
        org_id: UUID,
        pick_item: PickListItem,
        shortfall: Decimal,
    ) -> None:
        """Record a short-pick exception (EX-002 / ALT-004) via PR-03."""
        from app.services.pick_exception_service import PickExceptionService

        PickExceptionService(self.db).capture(
            org_id,
            {
                "pick_list_item_id": pick_item.id,
                "reason_code": "insufficient_quantity",
                "severity": "warning",
                "quantity": shortfall,
            },
        )

    def _capture_scan_exception(
        self,
        org_id: UUID,
        pick_list_item_id: UUID,
        reason_code: str,
        quantity: Decimal,
        worker_id: UUID,
    ) -> None:
        """Record a reason-coded exception raised during a scan (EX-007)."""
        from app.services.pick_exception_service import PickExceptionService

        PickExceptionService(self.db).capture(
            org_id,
            {
                "pick_list_item_id": pick_list_item_id,
                "reason_code": reason_code,
                "severity": "warning",
                "quantity": quantity,
            },
            reported_by=worker_id,
        )

    def record_pick_scan(  # noqa: C901
        self,
        pick_list_id: UUID,
        qr_data: str,
        worker_id: UUID,
        org_id: UUID,
        bin_location_id: UUID | None = None,
        reason_code: str | None = None,
        reason_quantity: Decimal | None = None,
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
            bin_location_id: Scanned source bin (wrong-bin hard stop when
                ``pick.require_bin_scan`` is enabled; WF-012 / ALT-001).

        Returns:
            Dict with scan result details.

        Raises:
            ResourceNotFoundException: If pick list not found.
            ValidationError: If pick list is not in a scannable state,
                item not on pick list, wrong bin scanned, or over-picking
                would occur.

        Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 11.2; WF-012, ALT-001
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

        # Wrong-bin hard stop (WF-012 / ALT-001 / EX-003).
        self.validate_bin(org_id, matching_pick_item, bin_location_id)

        # Serial validation (WF-014 / EX-005 / EX-006 / ALT-003).
        self.validate_serial(org_id, item, payload.id)

        # Check for over-picking (EX-021 tolerance)
        scanned_qty = Decimal(str(payload.qty))
        current_picked = Decimal(str(matching_pick_item.picked_qty or 0))
        required_qty = Decimal(str(matching_pick_item.qty))
        new_picked = current_picked + scanned_qty

        self.validate_over_pick(org_id, required_qty, new_picked)

        # Increment picked_qty
        matching_pick_item.picked_qty = new_picked

        # Decrement bin stock if bin_location_id is set
        if matching_pick_item.bin_location_id:
            from app.models.bin_stock_level import InventoryStatus
            from app.services.bin_stock_service import BinStockService

            bin_stock_service = BinStockService(self.db)
            bin_stock = bin_stock_service.remove_stock(
                bin_id=matching_pick_item.bin_location_id,
                item_id=item.id,
                quantity=scanned_qty,
                org_id=org_id,
                batch_number=payload.batch,
            )

            # Once this pick line is fully satisfied, release the worker's
            # reservation and advance the source bin stock to 'picked' (WF-016).
            if new_picked >= required_qty:
                bin_stock_service.transition_status(
                    bin_stock,
                    InventoryStatus.PICKED.value,
                    user_id=worker_id,
                    commit=False,
                )
                self.reservation_service.release(
                    bin_id=matching_pick_item.bin_location_id,
                    worker_id=worker_id,
                    org_id=org_id,
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

        # Movement ledger (WF-016) — idempotent posting via PR-04 replay guard.
        if matching_pick_item.bin_location_id:
            from app.services.bin_stock_service import BinStockService

            BinStockService(self.db).record_pick_movement(
                org_id=org_id,
                product_id=item.id,
                warehouse_id=matching_pick_item.warehouse_id,
                quantity=scanned_qty,
                reference_type="pick_scan",
                reference_id=scan_event.id,
                performed_by=worker_id,
                notes=f"Pick from bin {matching_pick_item.bin_location_id}",
            )

        self.db.commit()
        self.db.refresh(matching_pick_item)
        self.db.refresh(pick_list)

        # Damage/hold reason capture at scan (EX-007 / ALT-005).
        if reason_code:
            self._capture_scan_exception(
                org_id,
                matching_pick_item.id,
                reason_code,
                reason_quantity if reason_quantity is not None else scanned_qty,
                worker_id,
            )

        return {
            "pick_list_id": str(pick_list_id),
            "pick_list_status": pick_list.status.value,
            "pick_list_item_id": str(matching_pick_item.id),
            "item_id": str(item.id),
            "sku": payload.sku,
            "serial_no": payload.id,
            "scanned_qty": payload.qty,
            "picked_qty": float(matching_pick_item.picked_qty),
            "required_qty": float(matching_pick_item.qty),
            "remaining_qty": float(required_qty - new_picked),
            "batch": payload.batch,
        }

    def complete_pick_list(self, pick_list_id: UUID, org_id: UUID) -> PickList:
        """Mark a pick list as COMPLETED.

        Validates every line against the short-pick policy (``allow_short_pick``
        + ``short_pick_approval_threshold``): fully-picked lines pass; within-
        policy short lines record an ``insufficient_quantity`` exception and
        complete; disallowed / over-threshold short lines block completion.

        Args:
            pick_list_id: The pick list to complete.
            org_id: Organization ID for scoping.

        Returns:
            The updated PickList.

        Raises:
            ResourceNotFoundException: If pick list not found.
            ValidationError: If a short-pick is disallowed or over-threshold,
                or the pick list is not in a completable state.

        Requirements: 10.6, 10.7, 11.1; WF-015, EX-002, ALT-004
        """
        pick_list = self.repo.get_by_id(pick_list_id, org_id)
        if not pick_list:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")

        if pick_list.status not in (PickListStatus.DRAFT, PickListStatus.IN_PROGRESS):
            raise ValidationError(
                f"Cannot complete pick list with status '{pick_list.status.value}'. "
                f"Pick list must be in 'draft' or 'in_progress' status."
            )

        # Validate all items are fully picked (short-pick policy, EX-002 / ALT-004).
        for item in pick_list.items:
            shortfall = self.validate_short_pick(org_id, item)
            if shortfall is not None:
                self._capture_short_pick_exception(org_id, item, shortfall)

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

    def assign_worker(
        self, pick_list_id: UUID, worker_id: UUID, org_id: UUID
    ) -> PickList:
        """Assign (or reassign) a worker to a pick list.

        Requirements: worker assignment for pick lists.
        """
        pick_list = self.repo.get_by_id(pick_list_id, org_id)
        if not pick_list:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")

        pick_list.assigned_to = worker_id
        self.db.commit()
        self.db.refresh(pick_list)
        return pick_list

    # ------------------------------------------------------------------
    # TASK ACCEPT (PR-14 / T-14, WF-010)
    # ------------------------------------------------------------------

    def accept_task(
        self,
        pick_list_id: UUID,
        org_id: UUID,
        worker_id: UUID,
    ) -> PickList:
        """Record a worker accepting the pick task (WF-010).

        Sets ``accepted_at``/``accepted_by`` (idempotent on the first accept)
        and moves a ``draft`` pick list to ``in_progress``.

        Raises:
            ResourceNotFoundException: pick list not found.
            ValidationError: pick list not in an acceptable state.
        """
        pick_list = (
            self.db.query(PickList)
            .filter(
                PickList.id == pick_list_id,
                PickList.organization_id == org_id,
            )
            .first()
        )
        if pick_list is None:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")

        if pick_list.status not in (PickListStatus.DRAFT, PickListStatus.IN_PROGRESS):
            raise ValidationError(
                f"Cannot accept pick list with status '{pick_list.status.value}'"
            )

        if pick_list.accepted_at is None:
            pick_list.accepted_at = datetime.now(UTC)
        pick_list.accepted_by = worker_id
        pick_list.assigned_to = worker_id
        if pick_list.status == PickListStatus.DRAFT:
            pick_list.status = PickListStatus.IN_PROGRESS

        self.db.commit()
        self.db.refresh(pick_list)
        return pick_list

    # ------------------------------------------------------------------
    # PRIORITIZATION + TASK AGING (PR-12 / T-12, WF-007, ALT-011)
    # ------------------------------------------------------------------

    def update_priority(
        self,
        pick_list_id: UUID,
        data: dict,
        org_id: UUID,
    ) -> PickList:
        """Set manual priority/cutoff/wave/route/SLA on a pick list (WF-007).

        Only the fields present (and non-null) in ``data`` are updated.
        """
        pick_list = (
            self.db.query(PickList)
            .filter(
                PickList.id == pick_list_id,
                PickList.organization_id == org_id,
            )
            .first()
        )
        if pick_list is None:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")

        for field in (
            "priority",
            "dispatch_cutoff",
            "wave",
            "route",
            "sla_minutes",
        ):
            if field in data and data[field] is not None:
                setattr(pick_list, field, data[field])

        self.db.commit()
        self.db.refresh(pick_list)
        return pick_list

    @staticmethod
    def priority_sort_key(priority_fields: list[str], pl) -> tuple:
        """Canonical task-prioritization sort key (WF-007).

        Manual ``priority`` (higher = more urgent) is always first. The
        configured ``priority_fields`` then refine the order:

        - ``cutoff`` → earlier dispatch cutoff first (``None`` last)
        - ``wave`` → wave sequence ascending
        - ``route`` → route code ascending

        Falls back to ``created_at`` ascending (oldest task first).
        """
        key: list = [-1 * int(pl.priority or 0)]
        for field in priority_fields:
            if field == "cutoff":
                cutoff = getattr(pl, "dispatch_cutoff", None)
                key.append(cutoff.timestamp() if cutoff is not None else float("inf"))
            elif field == "wave":
                key.append(getattr(pl, "wave", None) or "\uffff")
            elif field == "route":
                key.append(getattr(pl, "route", None) or "\uffff")
        created = getattr(pl, "created_at", None)
        key.append(created.timestamp() if created is not None else float("inf"))
        return tuple(key)

    @staticmethod
    def aging_info(
        pl,
        threshold_minutes: int,
        now: datetime | None = None,
    ) -> dict:
        """Compute task-aging status (ALT-011).

        Aging is measured from ``created_at`` (falling back to ``pick_date``)
        against the effective SLA: ``sla_minutes`` on the pick list if set,
        otherwise ``pick.aging_threshold_minutes``.

        Returns ``{"age_minutes": int, "is_aging": bool}``.
        """
        created = getattr(pl, "created_at", None) or getattr(pl, "pick_date", None)
        if created is None:
            return {"age_minutes": 0, "is_aging": False}

        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)

        sla = getattr(pl, "sla_minutes", None)
        effective = sla if sla is not None else threshold_minutes

        current = now or datetime.now(UTC)
        age_minutes = max(0, int((current - created).total_seconds() // 60))
        return {
            "age_minutes": age_minutes,
            "is_aging": age_minutes >= effective,
        }

    # ------------------------------------------------------------------
    # STAGING (PR-10 / T-10, WF-019/020)
    # ------------------------------------------------------------------

    def validate_staging_lane(
        self,
        org_id: UUID,
        staging_location_id: UUID,
    ) -> WarehouseLocation:
        """Return the staging lane, or raise (EX-019/020 — staging unavailable).

        A staging lane is a ``warehouse_locations`` row with
        ``location_type = 'staging'``.
        """
        location = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id == staging_location_id,
                WarehouseLocation.organization_id == org_id,
            )
            .first()
        )
        if location is None:
            raise ValidationError(
                f"Staging lane {staging_location_id} not found"
            )
        if location.location_type != LocationType.STAGING.value:
            raise ValidationError(
                f"Location {staging_location_id} is not a staging lane "
                f"(type '{location.location_type}')"
            )
        return location

    def stage_transfer(
        self,
        pick_list_id: UUID,
        staging_location_id: UUID,
        org_id: UUID,
    ) -> PickList:
        """Assign a staging lane and move picked stock to ``in_transit_to_stage``.

        Raises:
            ValidationError: invalid staging lane, or pick list not in a
                stageable state.
        """
        pick_list = self.repo.get_by_id(pick_list_id, org_id)
        if not pick_list:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")

        if pick_list.status not in (PickListStatus.DRAFT, PickListStatus.IN_PROGRESS):
            raise ValidationError(
                f"Cannot stage pick list with status '{pick_list.status.value}'"
            )

        self.validate_staging_lane(org_id, staging_location_id)

        pick_list.staging_location_id = staging_location_id

        # Move each picked bin-stock record to in_transit_to_stage (WF-016).
        from app.models.bin_stock_level import BinStockLevel, InventoryStatus
        from app.services.bin_stock_service import BinStockService

        bin_stock_service = BinStockService(self.db)
        bin_ids = {
            item.bin_location_id for item in pick_list.items if item.bin_location_id
        }
        for bin_id in bin_ids:
            records = (
                self.db.query(BinStockLevel)
                .filter(
                    BinStockLevel.bin_location_id == bin_id,
                    BinStockLevel.organization_id == org_id,
                    BinStockLevel.inventory_status == InventoryStatus.PICKED.value,
                )
                .all()
            )
            for record in records:
                bin_stock_service.transition_status(
                    record,
                    InventoryStatus.IN_TRANSIT_TO_STAGE.value,
                    commit=False,
                )

        self.db.commit()
        self.db.refresh(pick_list)
        return pick_list

    def validate_stage_scan(
        self,
        pick_list: PickList,
        staging_location_id: UUID,
    ) -> None:
        """Raise if the scanned lane is wrong or no lane is assigned (ALT-008)."""
        if pick_list.staging_location_id is None:
            raise ValidationError(
                "Pick list has not been transferred to a staging lane"
            )
        if staging_location_id != pick_list.staging_location_id:
            raise ValidationError(
                f"Wrong staging lane: expected {pick_list.staging_location_id}, "
                f"scanned {staging_location_id}"
            )

    def stage_scan(
        self,
        pick_list_id: UUID,
        staging_location_id: UUID,
        org_id: UUID,
    ) -> PickList:
        """Validate the scanned staging lane and mark the pick list staged.

        Raises:
            ValidationError: wrong lane scanned (ALT-008), or the pick list
                has not been transferred to a staging lane.
        """
        pick_list = self.repo.get_by_id(pick_list_id, org_id)
        if not pick_list:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")

        self.validate_stage_scan(pick_list, staging_location_id)

        if pick_list.staged_at is None:
            pick_list.staged_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(pick_list)
        return pick_list

    # ------------------------------------------------------------------
    # HANDLING UNITS (PR-11 / T-11, WF-018)
    # ------------------------------------------------------------------

    def validate_handling_unit_assignment(
        self,
        org_id: UUID,
        pick_list_item_id: UUID,
        handling_unit_id: UUID,
    ) -> None:
        """Enforce handling-unit rules when ``pick.enable_handling_unit`` is on.

        - Flag off → skip (legacy).
        - Unknown handling unit → ResourceNotFoundException.
        - Handling unit already assigned to another pick item → ValidationError
          (duplicate HU rejected).
        """
        from app.models.handling_unit import HandlingUnit
        from app.services.pick_settings_service import PickConfigResolver

        if not PickConfigResolver.from_org(self.db, org_id).get_bool(
            "enable_handling_unit"
        ):
            return

        hu = (
            self.db.query(HandlingUnit)
            .filter(
                HandlingUnit.id == handling_unit_id,
                HandlingUnit.organization_id == org_id,
            )
            .first()
        )
        if hu is None:
            raise ResourceNotFoundException(
                f"Handling unit {handling_unit_id} not found"
            )

        other = (
            self.db.query(PickListItem)
            .filter(
                PickListItem.organization_id == org_id,
                PickListItem.handling_unit_id == handling_unit_id,
                PickListItem.id != pick_list_item_id,
            )
            .first()
        )
        if other is not None:
            raise ValidationError(
                f"Handling unit {handling_unit_id} is already assigned to "
                f"another pick item"
            )

    def assign_handling_unit(
        self,
        pick_list_item_id: UUID,
        handling_unit_id: UUID,
        org_id: UUID,
    ) -> PickListItem:
        """Associate a handling unit with a pick list item (WF-018)."""
        pick_item = (
            self.db.query(PickListItem)
            .filter(
                PickListItem.id == pick_list_item_id,
                PickListItem.organization_id == org_id,
            )
            .first()
        )
        if pick_item is None:
            raise ResourceNotFoundException(
                f"Pick list item {pick_list_item_id} not found"
            )

        self.validate_handling_unit_assignment(
            org_id, pick_list_item_id, handling_unit_id
        )
        pick_item.handling_unit_id = handling_unit_id
        self.db.commit()
        self.db.refresh(pick_item)
        return pick_item

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
            "assigned_to": pl.assigned_to,
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
                    "per_case_qty": item.per_case_qty,
                    "case_qty": item.case_qty,
                    "loose_qty": item.loose_qty,
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
                "per_case_qty": item.per_case_qty,
                "case_qty": item.case_qty,
                "loose_qty": item.loose_qty,
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
            "assigned_to": pl.assigned_to,
            "completed_at": pl.completed_at,
            "created_by": pl.created_by,
            "updated_by": pl.updated_by,
            "created_at": pl.created_at,
            "updated_at": pl.updated_at,
            "items": enriched_items,
        }

    @staticmethod
    def _to_list_item(pl, aging_threshold: int | None = None) -> dict:
        aging = (
            PickListService.aging_info(pl, aging_threshold)
            if aging_threshold is not None
            else {"age_minutes": 0, "is_aging": False}
        )
        return {
            "id": pl.id,
            "organization_id": pl.organization_id,
            "pick_list_no": pl.pick_list_no,
            "warehouse_id": pl.warehouse_id,
            "status": pl.status.value if pl.status else None,
            "pick_date": pl.pick_date,
            "reference_type": pl.reference_type,
            "reference_id": pl.reference_id,
            "assigned_to": pl.assigned_to,
            "items_count": len(pl.items) if pl.items else 0,
            "created_at": pl.created_at,
            "priority": pl.priority,
            "dispatch_cutoff": pl.dispatch_cutoff,
            "wave": pl.wave,
            "route": pl.route,
            "sla_minutes": pl.sla_minutes,
            "age_minutes": aging["age_minutes"],
            "is_aging": aging["is_aging"],
        }
