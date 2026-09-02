"""Outbound service for managing dispatch records and stock deduction.

Handles the outbound dispatch workflow:
- Create dispatch records from verified gate sessions
- Decrement warehouse stock levels for dispatched items
- Generate unique dispatch numbers
- List and retrieve dispatch records with filters

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StateError
from app.models.dispatch_record import DispatchRecord
from app.models.gate_verification import GateVerificationSession
from app.models.pick_list import PickList, PickListItem
from app.models.stock_level import StockLevel


class OutboundService:
    """Service for managing dispatch records and outbound stock deduction."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # CREATE DISPATCH
    # ------------------------------------------------------------------

    def create_dispatch(self, gate_session_id: UUID, org_id: UUID) -> dict:
        """
        Create a dispatch record from a verified gate verification session.

        Validates the gate session is VERIFIED, creates a dispatch record with
        pick_list_id, gate_session_id, vehicle/driver details, invoice_reference
        from the pick list, generates a unique dispatch_number, and decrements
        warehouse stock_levels for all dispatched items.

        Args:
            gate_session_id: UUID of the verified gate verification session.
            org_id: Organization UUID for tenant isolation.

        Returns:
            Dictionary representation of the created DispatchRecord.

        Raises:
            NotFoundError: If gate session is not found.
            StateError: If gate session is not in VERIFIED status.

        Requirements: 13.1, 13.4, 13.5
        """
        # Fetch the gate session
        gate_session = (
            self.db.query(GateVerificationSession)
            .filter(
                GateVerificationSession.id == gate_session_id,
                GateVerificationSession.organization_id == org_id,
            )
            .first()
        )

        if not gate_session:
            raise NotFoundError(
                message="Gate verification session not found",
                entity_type="GateVerificationSession",
                entity_id=str(gate_session_id),
            )

        if gate_session.status != "verified":
            raise StateError(
                message="Gate session must be in VERIFIED status to create dispatch",
                current_state=gate_session.status,
                required_state=["verified"],
            )

        # Fetch the associated pick list
        pick_list = (
            self.db.query(PickList)
            .filter(
                PickList.id == gate_session.pick_list_id,
                PickList.organization_id == org_id,
            )
            .first()
        )

        if not pick_list:
            raise NotFoundError(
                message="Associated pick list not found",
                entity_type="PickList",
                entity_id=str(gate_session.pick_list_id),
            )

        # Generate unique dispatch number
        from app.services.document_numbering_service import DocumentNumberingService

        dispatch_number = DocumentNumberingService(self.db).get_next_number(
            org_id, "dispatch"
        )

        # Create the dispatch record
        dispatch_record = DispatchRecord(
            organization_id=org_id,
            dispatch_number=dispatch_number,
            pick_list_id=gate_session.pick_list_id,
            gate_session_id=gate_session_id,
            invoice_reference=pick_list.invoice_reference,
            vehicle_number=gate_session.vehicle_number,
            driver_name=gate_session.driver_name,
            dispatched_at=datetime.now(UTC),
        )
        self.db.add(dispatch_record)
        self.db.flush()

        # Update pick list with dispatch record reference (Requirement 13.2)
        pick_list.dispatch_record_id = dispatch_record.id

        # Decrement warehouse stock levels for all dispatched items (Requirement 13.4)
        self._decrement_stock_levels(pick_list, org_id)

        # Propagate picked serials into the internal-transfer ASN (P1).
        self._propagate_transfer_serials(pick_list, org_id)

        self.db.commit()
        self.db.refresh(dispatch_record)

        return self._to_response(dispatch_record)

    def _propagate_transfer_serials(self, pick_list: PickList, org_id: UUID) -> None:
        """Propagate picked serials into the internal-transfer ASN at dispatch.

        When the pick list fulfils an internal-transfer ASN
        (``reference_type == 'asn_order'``), copy each line's ``serial_nos``
        into the ASN items + ``asn_order_serial_lines`` and write
        ``SerialNoHistory`` (``transfer_out``) rows for chain of custody.
        """
        import logging

        logger = logging.getLogger(__name__)

        if pick_list.reference_type != "asn_order" or not pick_list.reference_id:
            return

        from app.models.asn_order import AsnOrder, AsnOrderItem, AsnOrderSerialLine
        from app.models.serial_no import SerialNo, SerialNoHistory

        asn_order = (
            self.db.query(AsnOrder)
            .filter(
                AsnOrder.id == pick_list.reference_id,
                AsnOrder.organization_id == org_id,
            )
            .first()
        )
        if asn_order is None or asn_order.asn_type != "internal_transfer":
            return

        # Serialize concurrent dispatches for the same ASN: lock the ASN row so
        # two simultaneous dispatches cannot both build the same "existing"
        # snapshot and insert duplicate serial lines / transfer_out history.
        self.db.query(AsnOrder).filter(AsnOrder.id == asn_order.id).with_for_update().first()

        dest_warehouse_id = asn_order.warehouse_id_to
        source_warehouse_id = pick_list.warehouse_id

        # Keep the operation idempotent across repeat dispatch calls.
        existing = set(
            self.db.query(AsnOrderSerialLine.serial_no)
            .filter(AsnOrderSerialLine.asn_order_id == asn_order.id)
            .scalars()
            .all()
        )

        for line in pick_list.items:
            asn_item = (
                self.db.query(AsnOrderItem)
                .filter(
                    AsnOrderItem.asn_order_id == asn_order.id,
                    AsnOrderItem.item_id == line.item_id,
                )
                .first()
            )
            # Record the quantity actually dispatched (picked) for both
            # serialized and non-serialized lines, so the transfer stock entry
            # doesn't fall back to the full ordered quantity.
            if asn_item is not None:
                asn_item.shipped_qty = line.picked_qty or line.qty

            serials = [s for s in (line.serial_nos or []) if s]
            if not serials:
                continue

            if asn_item is not None:
                merged = list(dict.fromkeys((asn_item.serial_nos or []) + serials))
                asn_item.serial_nos = merged

            for serial_no in serials:
                if serial_no in existing:
                    continue
                self.db.add(
                    AsnOrderSerialLine(
                        organization_id=org_id,
                        asn_order_id=asn_order.id,
                        asn_item_id=asn_item.id if asn_item else None,
                        item_id=line.item_id,
                        serial_no=serial_no,
                        bin_location_id=line.bin_location_id,
                    )
                )
                existing.add(serial_no)

                serial_row = (
                    self.db.query(SerialNo)
                    .filter(
                        SerialNo.organization_id == org_id,
                        SerialNo.item_id == line.item_id,
                        SerialNo.serial_no == serial_no,
                    )
                    .first()
                )
                if serial_row is not None:
                    serial_row.status = "in_transit"
                    self.db.add(
                        SerialNoHistory(
                            organization_id=org_id,
                            serial_no_id=serial_row.id,
                            transaction_type="transfer_out",
                            transaction_id=asn_order.id,
                            from_warehouse_id=source_warehouse_id,
                            to_warehouse_id=dest_warehouse_id,
                            remarks=(
                                f"Internal transfer ASN {asn_order.asn_order_no}"
                            ),
                        )
                    )

        logger.info(
            "Propagated transfer serials for ASN '%s' at dispatch",
            asn_order.asn_order_no,
        )

        # Accounting traceability: a MATERIAL_TRANSFER stock entry for the move.
        self._create_transfer_stock_entry(asn_order, org_id)

    def _create_transfer_stock_entry(self, asn_order, org_id: UUID) -> None:
        """Create a submitted MATERIAL_TRANSFER stock entry at dispatch (idempotent)."""
        import logging

        logger = logging.getLogger(__name__)

        if asn_order.linked_stock_entry_id:
            return

        from datetime import UTC, datetime

        from app.models.asn_order import AsnOrderSerialLine
        from app.schemas.stock_entry import StockEntryCreate, StockEntryItemCreate
        from app.services.stock_entry_service import StockEntryService

        serial_lines = (
            self.db.query(AsnOrderSerialLine)
            .filter(AsnOrderSerialLine.asn_order_id == asn_order.id)
            .all()
        )
        serials_by_item: dict = {}
        for line in serial_lines:
            serials_by_item.setdefault(line.item_id, []).append(line.serial_no)

        items = []
        for item in asn_order.items:
            shipped_qty = float(item.shipped_qty or 0)
            if shipped_qty <= 0:
                continue
            items.append(
                StockEntryItemCreate(
                    item_id=item.item_id,
                    qty=shipped_qty,
                    uom=item.uom,
                    serial_nos=serials_by_item.get(item.item_id) or None,
                )
            )
        if not items:
            return

        # Create as a DRAFT and submit it so stock levels are updated and the
        # movement audit rows are written. Creating it directly "submitted"
        # only persists the header without ever moving stock.
        entry = StockEntryService(self.db).create(
            StockEntryCreate(
                stock_entry_type="material_transfer",
                from_warehouse_id=asn_order.warehouse_id_from,
                to_warehouse_id=asn_order.warehouse_id_to,
                posting_date=datetime.now(UTC),
                reference_type="asn_order",
                reference_id=asn_order.id,
                remarks=f"Internal transfer ASN {asn_order.asn_order_no}",
                items=items,
            ),
            org_id,
            asn_order.created_by,
        )
        asn_order.linked_stock_entry_id = entry.id
        self.db.flush()
        StockEntryService(self.db).submit(entry.id, org_id, asn_order.created_by)
        logger.info(
            "Created MATERIAL_TRANSFER stock entry %s for ASN '%s'",
            entry.stock_entry_no,
            asn_order.asn_order_no,
        )

    # ------------------------------------------------------------------
    # LIST DISPATCHES
    # ------------------------------------------------------------------

    def list_dispatches(
        self,
        org_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        vehicle_number: str | None = None,
        invoice_reference: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """
        List dispatch records with optional filters.

        Args:
            org_id: Organization UUID for tenant isolation.
            date_from: Filter dispatches from this date (inclusive).
            date_to: Filter dispatches up to this date (inclusive).
            vehicle_number: Filter by vehicle number (partial match).
            invoice_reference: Filter by invoice reference (partial match).
            page: Page number (1-indexed).
            page_size: Number of records per page.

        Returns:
            Dictionary with dispatches list and pagination metadata.

        Requirements: 13.3
        """
        query = self.db.query(DispatchRecord).filter(
            DispatchRecord.organization_id == org_id
        )

        # Apply filters
        if date_from:
            query = query.filter(DispatchRecord.dispatched_at >= date_from)
        if date_to:
            query = query.filter(DispatchRecord.dispatched_at <= date_to)
        if vehicle_number:
            query = query.filter(
                DispatchRecord.vehicle_number.ilike(f"%{vehicle_number}%")
            )
        if invoice_reference:
            query = query.filter(
                DispatchRecord.invoice_reference.ilike(f"%{invoice_reference}%")
            )

        # Get total count
        total_items = query.count()

        # Apply pagination
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        offset = (page - 1) * page_size
        dispatches = (
            query.order_by(DispatchRecord.dispatched_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return {
            "dispatches": [self._to_response(d) for d in dispatches],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }

    # ------------------------------------------------------------------
    # GET DISPATCH
    # ------------------------------------------------------------------

    def get_dispatch(self, dispatch_id: UUID, org_id: UUID) -> dict:
        """
        Get a single dispatch record by ID.

        Args:
            dispatch_id: UUID of the dispatch record.
            org_id: Organization UUID for tenant isolation.

        Returns:
            Dictionary representation of the DispatchRecord.

        Raises:
            NotFoundError: If dispatch record is not found.

        Requirements: 13.3
        """
        dispatch_record = (
            self.db.query(DispatchRecord)
            .filter(
                DispatchRecord.id == dispatch_id,
                DispatchRecord.organization_id == org_id,
            )
            .first()
        )

        if not dispatch_record:
            raise NotFoundError(
                message="Dispatch record not found",
                entity_type="DispatchRecord",
                entity_id=str(dispatch_id),
            )

        return self._to_response(dispatch_record)

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _decrement_stock_levels(self, pick_list: PickList, org_id: UUID) -> None:
        """
        Decrement warehouse stock_levels for all items in the pick list.

        For each pick list item, finds the corresponding stock_level record
        and decrements quantity_on_hand by the picked quantity.

        Args:
            pick_list: The PickList whose items should be decremented.
            org_id: Organization UUID for tenant isolation.

        Requirements: 13.4
        """
        pick_list_items = (
            self.db.query(PickListItem)
            .filter(
                PickListItem.pick_list_id == pick_list.id,
                PickListItem.organization_id == org_id,
            )
            .all()
        )

        for item in pick_list_items:
            # Use picked_qty if available, otherwise fall back to qty
            dispatch_qty = item.picked_qty if item.picked_qty else item.qty

            if not dispatch_qty or dispatch_qty <= 0:
                continue

            stock_level = (
                self.db.query(StockLevel)
                .filter(
                    StockLevel.organization_id == org_id,
                    StockLevel.product_id == item.item_id,
                    StockLevel.warehouse_id == item.warehouse_id,
                )
                .first()
            )

            if stock_level:
                dispatch_qty_int = int(dispatch_qty)
                stock_level.quantity_on_hand = max(
                    0, (stock_level.quantity_on_hand or 0) - dispatch_qty_int
                )
                # Also update available quantity
                stock_level.quantity_available = max(
                    0,
                    (stock_level.quantity_on_hand or 0)
                    - (stock_level.quantity_reserved or 0),
                )

    def _to_response(self, dispatch_record: DispatchRecord) -> dict:
        """Convert a DispatchRecord model to a response dictionary."""
        return {
            "id": str(dispatch_record.id),
            "organization_id": str(dispatch_record.organization_id),
            "dispatch_number": dispatch_record.dispatch_number,
            "pick_list_id": str(dispatch_record.pick_list_id),
            "gate_session_id": str(dispatch_record.gate_session_id),
            "invoice_reference": dispatch_record.invoice_reference,
            "vehicle_number": dispatch_record.vehicle_number,
            "driver_name": dispatch_record.driver_name,
            "dispatched_at": (
                dispatch_record.dispatched_at.isoformat()
                if dispatch_record.dispatched_at
                else None
            ),
            "created_at": (
                dispatch_record.created_at.isoformat()
                if dispatch_record.created_at
                else None
            ),
            "updated_at": (
                dispatch_record.updated_at.isoformat()
                if dispatch_record.updated_at
                else None
            ),
        }
