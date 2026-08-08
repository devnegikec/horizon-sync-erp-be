"""Inbound service for managing scan sessions, receiving slips, and QR decoding.

Handles the inbound receiving workflow:
- Start/end scan sessions for dock workers
- Record QR scans with duplicate detection
- Generate receiving slips from closed sessions
- Provide session summaries with per-SKU/batch aggregation

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 14.1
"""

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.item_packaging_unit import ItemPackagingUnit
from app.models.qr_scan_event import QRScanEvent
from app.models.receiving_slip import ReceivingSlipItem
from app.models.scan_session import ScanSessionItem
from app.repositories.receiving_slip_repository import ReceivingSlipRepository
from app.repositories.scan_session_repository import ScanSessionRepository
from app.services.item_packaging_unit_service import ItemPackagingUnitService
from app.services.qr_decoder import decode_qr_payload


class InboundService:
    """Service for managing the inbound receiving workflow."""

    def __init__(self, db: Session):
        self.db = db
        self.session_repo = ScanSessionRepository(db)
        self.slip_repo = ReceivingSlipRepository(db)

    # ------------------------------------------------------------------
    # START SESSION
    # ------------------------------------------------------------------

    def start_session(
        self,
        worker_id: UUID,
        organization_id: UUID,
        warehouse_id: UUID,
        dock_location: str | None = None,
        asn_order_id: UUID | None = None,
    ) -> dict:
        """
        Create a new inbound scan session with status OPEN.

        Args:
            worker_id: UUID of the dock worker starting the session.
            organization_id: Organization UUID for tenant isolation.
            warehouse_id: UUID of the warehouse where receiving occurs.
            dock_location: Optional dock location identifier.
            asn_order_id: Optional ASN order UUID to link the session to.

        Returns:
            Dictionary representation of the created ScanSession.

        Requirements: 5.1
        """
        session_data = {
            "organization_id": organization_id,
            "session_type": "inbound",
            "worker_id": worker_id,
            "warehouse_id": warehouse_id,
            "dock_location": dock_location,
            "asn_order_id": asn_order_id,
            "status": "open",
            "total_boxes_scanned": 0,
            "started_at": datetime.now(UTC),
        }

        session = self.session_repo.create_session(session_data)

        return self._session_to_dict(session)

    # ------------------------------------------------------------------
    # RECORD SCAN
    # ------------------------------------------------------------------

    def record_scan(
        self,
        session_id: UUID,
        qr_data: str,
        worker_id: UUID,
        organization_id: UUID,
        device_type: str | None = None,
        os: str | None = None,
    ) -> dict:
        """
        Record a QR scan within an open session.

        Decodes the QR payload, checks for duplicate qr_identifier within
        the session, adds a ScanSessionItem, and records a scan event in
        the qr_scan_events table.

        Args:
            session_id: UUID of the active scan session.
            qr_data: Raw QR code payload string (JSON).
            worker_id: UUID of the worker performing the scan.
            organization_id: Organization UUID for tenant isolation.
            device_type: Optional device type (e.g., 'mobile', 'tablet').
            os: Optional operating system info.

        Returns:
            Dictionary with scan result including decoded payload and item info.

        Raises:
            NotFoundError: If session is not found.
            StateError: If session is not in OPEN status.
            ValidationError: If QR payload is invalid or duplicate scan detected.

        Requirements: 5.2, 5.3, 5.4, 14.1
        """
        # Fetch and validate session
        session = self.session_repo.get_by_id(session_id, organization_id)
        if session is None:
            raise NotFoundError(
                message="Scan session not found",
                entity_type="ScanSession",
                entity_id=str(session_id),
            )

        if session.status != "open":
            raise StateError(
                message="Cannot record scan on a closed session",
                current_state=session.status,
                required_state=["open"],
            )

        # Decode QR payload — supports both JSON and URL format QR codes
        payload = decode_qr_payload(qr_data, db=self.db)

        # Check for duplicate qr_identifier within this session
        existing_items = self.session_repo.get_items(session_id)
        for item in existing_items:
            if item.qr_identifier == payload.id:
                raise ValidationError(
                    message="Duplicate scan: this box has already been scanned in this session",
                    details=[
                        {
                            "field": "qr_identifier",
                            "reason": f"QR identifier '{payload.id}' already exists in session",
                        }
                    ],
                )

        # Resolve packaging unit from QR payload (best-effort — null if not found)
        packaging_unit_id = None
        if payload.packaging_unit_qr_id:
            pu = ItemPackagingUnitService().resolve_by_qr_identifier(
                payload.packaging_unit_qr_id, organization_id, self.db
            )
            if pu is not None:
                packaging_unit_id = pu.id

        # Add scan session item
        item_data = {
            "organization_id": organization_id,
            "qr_identifier": payload.id,
            "sku": payload.sku,
            "raw_quantity": payload.qty,
            "batch_number": payload.batch,
            "raw_qr_data": qr_data,
            "packaging_unit_id": packaging_unit_id,
        }
        scan_item = self.session_repo.add_item(session_id, item_data)

        # Record scan event in qr_scan_events table
        scan_event = QRScanEvent(
            organization_id=organization_id,
            serial_number=payload.id,
            scan_timestamp=datetime.now(UTC),
            device_type=device_type,
            os=os,
            extra_data={
                "scan_context": "inbound",
                "session_id": str(session_id),
                "worker_id": str(worker_id),
                "decoded_payload": {
                    "id": payload.id,
                    "sku": payload.sku,
                    "qty": payload.qty,
                    "batch": payload.batch,
                    "packaging_unit_qr_id": payload.packaging_unit_qr_id,
                },
            },
        )
        self.db.add(scan_event)
        self.db.commit()

        return {
            "scan_item_id": str(scan_item.id),
            "session_id": str(session_id),
            "qr_identifier": payload.id,
            "sku": payload.sku,
            "raw_quantity": payload.qty,
            "batch_number": payload.batch,
            "packaging_unit_id": str(packaging_unit_id) if packaging_unit_id else None,
            "scanned_at": scan_item.scanned_at.isoformat()
            if scan_item.scanned_at
            else None,
            "total_boxes_scanned": session.total_boxes_scanned,
        }

    # ------------------------------------------------------------------
    # END SESSION
    # ------------------------------------------------------------------

    def end_session(
        self,
        session_id: UUID,
        worker_id: UUID,
        organization_id: UUID,
    ) -> dict:
        """
        Close a scan session and generate a receiving slip.

        Sets the session status to 'closed', records the end timestamp,
        and generates a receiving slip from the session items grouped
        by SKU and batch number.

        Args:
            session_id: UUID of the scan session to close.
            worker_id: UUID of the worker ending the session.
            organization_id: Organization UUID for tenant isolation.

        Returns:
            Dictionary representation of the generated ReceivingSlip.

        Raises:
            NotFoundError: If session is not found.
            StateError: If session is not in OPEN status.

        Requirements: 5.5, 6.1, 6.2, 6.4, 6.5
        """
        # Fetch and validate session
        session = self.session_repo.get_by_id(session_id, organization_id)
        if session is None:
            raise NotFoundError(
                message="Scan session not found",
                entity_type="ScanSession",
                entity_id=str(session_id),
            )

        if session.status != "open":
            raise StateError(
                message="Session is already closed",
                current_state=session.status,
                required_state=["open"],
            )

        # Close the session
        closed_session = self.session_repo.close_session(session_id)

        # Get all items in the session
        items = self.session_repo.get_items(session_id)

        # Generate receiving slip
        slip = self._generate_receiving_slip(
            session=closed_session,
            items=items,
            organization_id=organization_id,
        )

        return self._slip_to_dict(slip)

    # ------------------------------------------------------------------
    # GET SESSION SUMMARY
    # ------------------------------------------------------------------

    def get_session_summary(
        self,
        session_id: UUID,
        organization_id: UUID,
    ) -> dict:
        """
        Get a summary of a scan session with per-SKU/batch aggregation.

        Returns total boxes scanned, per-SKU quantities, and per-batch
        breakdown.

        Args:
            session_id: UUID of the scan session.
            organization_id: Organization UUID for tenant isolation.

        Returns:
            Dictionary with session summary including aggregated data.

        Raises:
            NotFoundError: If session is not found.

        Requirements: 5.3, 5.6
        """
        session = self.session_repo.get_by_id(session_id, organization_id)
        if session is None:
            raise NotFoundError(
                message="Scan session not found",
                entity_type="ScanSession",
                entity_id=str(session_id),
            )

        items = self.session_repo.get_items(session_id)

        # Aggregate by SKU + batch
        sku_batch_agg: dict[tuple[str, str], dict] = defaultdict(
            lambda: {"quantity": 0, "box_count": 0}
        )
        for item in items:
            key = (item.sku, item.batch_number)
            sku_batch_agg[key]["quantity"] += item.raw_quantity
            sku_batch_agg[key]["box_count"] += 1

        # Build per-SKU summary
        sku_summary: dict[str, dict] = defaultdict(
            lambda: {"total_quantity": 0, "total_boxes": 0, "batches": []}
        )
        for (sku, batch), agg in sku_batch_agg.items():
            sku_summary[sku]["total_quantity"] += agg["quantity"]
            sku_summary[sku]["total_boxes"] += agg["box_count"]
            sku_summary[sku]["batches"].append(
                {
                    "batch_number": batch,
                    "quantity": agg["quantity"],
                    "box_count": agg["box_count"],
                }
            )

        items_breakdown = []
        for sku, summary in sku_summary.items():
            items_breakdown.append(
                {
                    "sku": sku,
                    "total_quantity": summary["total_quantity"],
                    "total_boxes": summary["total_boxes"],
                    "batches": summary["batches"],
                }
            )

        total_boxes = len(items)
        total_quantity = sum(item.raw_quantity for item in items)

        # Count distinct QSeal parent containers for true box count
        parent_boxes = self._count_distinct_qseal_parents(items, organization_id)
        total_boxes = parent_boxes if parent_boxes > 0 else total_boxes

        return {
            "session_id": str(session.id),
            "status": session.status,
            "session_type": session.session_type,
            "warehouse_id": str(session.warehouse_id),
            "worker_id": str(session.worker_id),
            "dock_location": session.dock_location,
            "started_at": session.started_at.isoformat()
            if session.started_at
            else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "total_boxes": total_boxes,
            "total_quantity": total_quantity,
            "items": items_breakdown,
        }

    # ------------------------------------------------------------------
    # GENERATE RECEIVING SLIP (public)
    # ------------------------------------------------------------------

    def generate_receiving_slip(
        self,
        session_id: UUID,
        organization_id: UUID,
    ) -> dict:
        """
        Generate a receiving slip from a closed scan session.

        Groups scan items by SKU+batch, computes totals, creates a
        ReceivingSlip with status PENDING_REVIEW, and creates
        ReceivingSlipItems for each group.

        Args:
            session_id: UUID of the closed scan session.
            organization_id: Organization UUID for tenant isolation.

        Returns:
            Dictionary representation of the generated ReceivingSlip.

        Raises:
            NotFoundError: If session is not found.
            StateError: If session is not in CLOSED status.

        Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
        """
        # Fetch and validate session
        session = self.session_repo.get_by_id(session_id, organization_id)
        if session is None:
            raise NotFoundError(
                message="Scan session not found",
                entity_type="ScanSession",
                entity_id=str(session_id),
            )

        if session.status != "closed":
            raise StateError(
                message="Cannot generate receiving slip from a session that is not closed",
                current_state=session.status,
                required_state=["closed"],
            )

        # Get all items in the session
        items = self.session_repo.get_items(session_id)

        if not items:
            raise ValidationError(
                message="Cannot generate receiving slip from an empty session",
                details=[
                    {
                        "field": "session_id",
                        "reason": "Session has no scanned items",
                    }
                ],
            )

        # Generate the slip
        slip = self._generate_receiving_slip(
            session=session,
            items=items,
            organization_id=organization_id,
        )

        return self._slip_to_dict(slip)

    # ------------------------------------------------------------------
    # APPROVE SLIP
    # ------------------------------------------------------------------

    def approve_slip(
        self,
        slip_id: UUID,
        organization_id: UUID,
        worker_id: UUID | None = None,
    ) -> dict:
        """
        Approve a receiving slip, transitioning it to PENDING_PUTAWAY.

        Validates that the slip is in PENDING_REVIEW status before
        transitioning. Converts raw_quantity on each ScanSessionItem to
        Eaches using the associated ItemPackagingUnit.conversion_factor,
        then re-aggregates receiving_slip_items by (sku, batch_number)
        with the converted Eaches quantities. Rejected items are preserved
        and excluded from put-away and ASN delivered_qty updates.

        After transitioning, triggers put-away list generation via
        PutAwayService for accepted items only.

        Args:
            slip_id: UUID of the receiving slip to approve.
            organization_id: Organization UUID for tenant isolation.
            worker_id: Optional UUID of the worker to assign the put-away task to.

        Returns:
            Dictionary representation of the updated ReceivingSlip.

        Raises:
            NotFoundError: If slip is not found.
            StateError: If slip is not in PENDING_REVIEW status.
            HTTPException 422: If a referenced packaging unit is not found or
                inactive.

        Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
        """
        slip = self.slip_repo.get_by_id(slip_id, organization_id)
        if slip is None:
            raise NotFoundError(
                message="Receiving slip not found",
                entity_type="ReceivingSlip",
                entity_id=str(slip_id),
            )

        if slip.status != "pending_review":
            raise StateError(
                message="Receiving slip must be in pending_review status to approve",
                current_state=slip.status,
                required_state=["pending_review"],
            )

        # ------------------------------------------------------------------
        # Step 0: Save rejected items before regeneration
        # ------------------------------------------------------------------
        rejected_items = []
        for existing_item in slip.items:
            if existing_item.flag == "rejected":
                rejected_items.append(
                    {
                        "sku": existing_item.sku,
                        "batch_number": existing_item.batch_number,
                        "quantity": existing_item.quantity,
                        "box_count": existing_item.box_count,
                        "flag": "rejected",
                        "rejection_reason": existing_item.rejection_reason,
                        "rejected_by": existing_item.rejected_by,
                        "rejected_at": existing_item.rejected_at,
                        "notes": existing_item.notes,
                    }
                )

        # ------------------------------------------------------------------
        # Step 1: Fetch all ScanSessionItems for this slip's session
        # ------------------------------------------------------------------
        scan_items = (
            self.db.query(ScanSessionItem)
            .filter(ScanSessionItem.session_id == slip.session_id)
            .all()
        )

        # ------------------------------------------------------------------
        # Step 2: Convert raw_quantity → Eaches and aggregate by (sku, batch)
        # ------------------------------------------------------------------
        # key: (sku, batch_number) → {"eaches_qty": int, "box_count": int}
        slip_items_by_key: dict[tuple[str, str], dict] = defaultdict(
            lambda: {"eaches_qty": 0, "box_count": 0}
        )

        for scan_item in scan_items:
            if scan_item.packaging_unit_id is not None:
                pu = self.db.get(ItemPackagingUnit, scan_item.packaging_unit_id)
                if pu is None or not pu.is_active:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"Packaging unit {scan_item.packaging_unit_id} "
                            "not found or inactive. Cannot approve slip."
                        ),
                    )
                eaches_qty = int(scan_item.raw_quantity * pu.conversion_factor)
            else:
                eaches_qty = scan_item.raw_quantity

            key = (scan_item.sku, scan_item.batch_number)
            slip_items_by_key[key]["eaches_qty"] += eaches_qty
            slip_items_by_key[key]["box_count"] += 1

        # ------------------------------------------------------------------
        # Step 3: Delete existing receiving_slip_items and recreate with
        #         converted Eaches quantities (accepted) + rejected items
        # ------------------------------------------------------------------
        self.db.query(ReceivingSlipItem).filter(
            ReceivingSlipItem.slip_id == slip_id
        ).delete(synchronize_session="fetch")

        total_eaches = 0
        for (sku, batch_number), agg in slip_items_by_key.items():
            item_data = {
                "organization_id": organization_id,
                "sku": sku,
                "batch_number": batch_number,
                "quantity": agg["eaches_qty"],
                "box_count": agg["box_count"],
                "flag": "ok",
            }
            self.slip_repo.add_item(slip_id, item_data)
            total_eaches += agg["eaches_qty"]

        # Re-add rejected items (they stay in floating mode)
        for rejected in rejected_items:
            self.slip_repo.add_item(
                slip_id,
                {
                    "organization_id": organization_id,
                    **rejected,
                },
            )

        # Update total_items on the slip to reflect converted Eaches total
        slip.total_items = total_eaches

        # Recalculate total_boxes from session's scan items based on QSeal parents
        from app.models.scan_session import ScanSessionItem

        scan_items_for_boxes = (
            self.db.query(ScanSessionItem)
            .filter(ScanSessionItem.session_id == slip.session_id)
            .all()
        )
        parent_box_count = self._count_distinct_qseal_parents(
            scan_items_for_boxes, organization_id
        )
        if parent_box_count > 0:
            slip.total_boxes = parent_box_count

        self.db.flush()

        # ------------------------------------------------------------------
        # Step 4: Transition slip status to PENDING_PUTAWAY
        # ------------------------------------------------------------------
        updated_slip = self.slip_repo.update_status(slip_id, "pending_putaway")
        self.db.refresh(updated_slip)

        # Trigger put-away list generation (with optional worker assignment)
        # Only accepted items (flag='ok') are included in put-away
        from app.services.put_away_service import PutAwayService

        put_away_service = PutAwayService(self.db)
        put_away_service.generate_from_slip(
            slip_id, organization_id, worker_id=worker_id
        )

        # ------------------------------------------------------------------
        # Step 5: Update ASN delivered_qty for accepted items
        # ------------------------------------------------------------------
        if slip.asn_order_id:
            self._sync_asn_delivered_qty(slip.asn_order_id, organization_id)

        self.db.refresh(updated_slip)
        return self._slip_to_dict(updated_slip)

    # ------------------------------------------------------------------
    # SYNC ASN DELIVERED QTY
    # ------------------------------------------------------------------

    def _sync_asn_delivered_qty(
        self, asn_order_id: UUID, organization_id: UUID
    ) -> None:
        """Update delivered_qty on ASN items based on accepted receiving slips."""
        from sqlalchemy import func

        from app.models.asn_order import AsnOrder
        from app.models.receiving_slip import ReceivingSlip, ReceivingSlipItem

        asn_order = (
            self.db.query(AsnOrder)
            .filter(
                AsnOrder.id == asn_order_id, AsnOrder.organization_id == organization_id
            )
            .first()
        )
        if not asn_order:
            return

        # Get all receiving slip IDs linked to this ASN
        slip_ids_query = (
            self.db.query(ReceivingSlip.id)
            .filter(
                ReceivingSlip.asn_order_id == asn_order_id,
                ReceivingSlip.organization_id == organization_id,
                ReceivingSlip.status.in_(["pending_putaway", "putaway_complete"]),
            )
            .all()
        )
        slip_ids = [s[0] for s in slip_ids_query]

        if not slip_ids:
            return

        # Aggregate accepted qty per SKU across all slips
        accepted_by_sku = {}
        rows = (
            self.db.query(
                ReceivingSlipItem.sku,
                func.sum(ReceivingSlipItem.quantity).label("total"),
            )
            .filter(
                ReceivingSlipItem.slip_id.in_(slip_ids),
                ReceivingSlipItem.flag == "ok",
            )
            .group_by(ReceivingSlipItem.sku)
            .all()
        )
        for sku, total in rows:
            accepted_by_sku[sku] = int(total) if total else 0

        # Update each ASN item's delivered_qty
        all_delivered = True
        any_delivered = False
        for asn_item in asn_order.items:
            sku = asn_item.item.sku if asn_item.item else None
            delivered = accepted_by_sku.get(sku, 0)
            asn_item.delivered_qty = delivered
            if delivered > 0:
                any_delivered = True
            if delivered < int(asn_item.qty):
                all_delivered = False

        # Update ASN status based on delivery progress
        if all_delivered and any_delivered:
            asn_order.status = "delivered"
        elif any_delivered and not all_delivered:
            asn_order.status = "partially_delivered"

        self.db.commit()

    # ------------------------------------------------------------------
    # REJECT SLIP
    # ------------------------------------------------------------------

    def reject_slip(
        self,
        slip_id: UUID,
        reason: str,
        organization_id: UUID,
    ) -> dict:
        """
        Reject a receiving slip with a reason.

        Validates that the slip is in PENDING_REVIEW status before
        transitioning to REJECTED.

        Args:
            slip_id: UUID of the receiving slip to reject.
            reason: Reason for rejection.
            organization_id: Organization UUID for tenant isolation.

        Returns:
            Dictionary representation of the updated ReceivingSlip.

        Raises:
            NotFoundError: If slip is not found.
            StateError: If slip is not in PENDING_REVIEW status.
            ValidationError: If reason is empty.

        Requirements: 7.4
        """
        if not reason or not reason.strip():
            raise ValidationError(
                message="Rejection reason is required",
                details=[
                    {
                        "field": "reason",
                        "reason": "Rejection reason must be a non-empty string",
                    }
                ],
            )

        slip = self.slip_repo.get_by_id(slip_id, organization_id)
        if slip is None:
            raise NotFoundError(
                message="Receiving slip not found",
                entity_type="ReceivingSlip",
                entity_id=str(slip_id),
            )

        if slip.status != "pending_review":
            raise StateError(
                message="Receiving slip must be in pending_review status to reject",
                current_state=slip.status,
                required_state=["pending_review"],
            )

        updated_slip = self.slip_repo.update_rejection_reason(slip_id, reason.strip())
        self.db.refresh(updated_slip)
        return self._slip_to_dict(updated_slip)

    # ------------------------------------------------------------------
    # FLAG LINE ITEM
    # ------------------------------------------------------------------

    def flag_line_item(
        self,
        slip_id: UUID,
        item_id: UUID,
        flag: str,
        notes: str | None,
        organization_id: UUID,
    ) -> dict:
        """
        Flag a receiving slip line item as SHORT or DAMAGED.

        Validates that the slip exists and is in PENDING_REVIEW status,
        and that the item belongs to the slip.

        Args:
            slip_id: UUID of the receiving slip.
            item_id: UUID of the receiving slip item to flag.
            flag: Flag value ('short' or 'damaged').
            notes: Optional notes about the discrepancy.
            organization_id: Organization UUID for tenant isolation.

        Returns:
            Dictionary representation of the updated ReceivingSlipItem.

        Raises:
            NotFoundError: If slip or item is not found.
            StateError: If slip is not in PENDING_REVIEW status.
            ValidationError: If flag value is invalid.

        Requirements: 7.5
        """
        valid_flags = ("short", "damaged")
        if flag not in valid_flags:
            raise ValidationError(
                message=f"Invalid flag value. Must be one of: {', '.join(valid_flags)}",
                details=[
                    {
                        "field": "flag",
                        "reason": f"Flag must be one of: {', '.join(valid_flags)}",
                    }
                ],
            )

        # Validate slip exists and is in correct state
        slip = self.slip_repo.get_by_id(slip_id, organization_id)
        if slip is None:
            raise NotFoundError(
                message="Receiving slip not found",
                entity_type="ReceivingSlip",
                entity_id=str(slip_id),
            )

        if slip.status != "pending_review":
            raise StateError(
                message="Receiving slip must be in pending_review status to flag items",
                current_state=slip.status,
                required_state=["pending_review"],
            )

        # Validate item exists and belongs to this slip
        item = self.slip_repo.get_item_by_id(item_id, organization_id)
        if item is None:
            raise NotFoundError(
                message="Receiving slip item not found",
                entity_type="ReceivingSlipItem",
                entity_id=str(item_id),
            )

        if item.slip_id != slip_id:
            raise ValidationError(
                message="Item does not belong to the specified receiving slip",
                details=[
                    {
                        "field": "item_id",
                        "reason": f"Item {item_id} does not belong to slip {slip_id}",
                    }
                ],
            )

        # Update the flag
        updated_item = self.slip_repo.update_item_flag(item_id, flag, notes)

        return {
            "id": str(updated_item.id),
            "slip_id": str(updated_item.slip_id),
            "sku": updated_item.sku,
            "batch_number": updated_item.batch_number,
            "quantity": updated_item.quantity,
            "box_count": updated_item.box_count,
            "flag": updated_item.flag,
            "notes": updated_item.notes,
        }

    # ------------------------------------------------------------------
    # REJECT SLIP ITEM (Item-Level)
    # ------------------------------------------------------------------

    def reject_slip_item(
        self,
        slip_id: UUID,
        item_id: UUID,
        reason: str,
        organization_id: UUID,
        rejected_by: UUID | None = None,
        notes: str | None = None,
    ) -> dict:
        """
        Reject an individual receiving slip line item.

        The item enters "floating mode" — it is recorded on the slip but:
        - Does NOT update stock levels
        - Does NOT generate put-away tasks
        - Does NOT count toward ASN delivered_qty

        Args:
            slip_id: UUID of the receiving slip.
            item_id: UUID of the receiving slip item to reject.
            reason: Reason for rejection.
            organization_id: Organization UUID for tenant isolation.
            rejected_by: UUID of the user performing the rejection.
            notes: Optional additional notes.

        Returns:
            Dictionary representation of the rejected item.

        Raises:
            NotFoundError: If slip or item not found.
            StateError: If slip is not in pending_review status.
            ValidationError: If item doesn't belong to slip.
        """
        if not reason or not reason.strip():
            raise ValidationError(
                message="Rejection reason is required",
                details=[
                    {"field": "reason", "reason": "Rejection reason must be non-empty"}
                ],
            )

        slip = self.slip_repo.get_by_id(slip_id, organization_id)
        if slip is None:
            raise NotFoundError(
                message="Receiving slip not found",
                entity_type="ReceivingSlip",
                entity_id=str(slip_id),
            )

        if slip.status != "pending_review":
            raise StateError(
                message="Receiving slip must be in pending_review status to reject items",
                current_state=slip.status,
                required_state=["pending_review"],
            )

        item = self.slip_repo.get_item_by_id(item_id, organization_id)
        if item is None:
            raise NotFoundError(
                message="Receiving slip item not found",
                entity_type="ReceivingSlipItem",
                entity_id=str(item_id),
            )

        if item.slip_id != slip_id:
            raise ValidationError(
                message="Item does not belong to the specified receiving slip",
                details=[
                    {
                        "field": "item_id",
                        "reason": f"Item {item_id} does not belong to slip {slip_id}",
                    }
                ],
            )

        updated_item = self.slip_repo.reject_item(
            item_id, reason.strip(), rejected_by=rejected_by, notes=notes
        )

        return {
            "id": str(updated_item.id),
            "slip_id": str(updated_item.slip_id),
            "sku": updated_item.sku,
            "batch_number": updated_item.batch_number,
            "quantity": updated_item.quantity,
            "box_count": updated_item.box_count,
            "flag": updated_item.flag,
            "rejection_reason": updated_item.rejection_reason,
            "notes": updated_item.notes,
            "rejected_at": updated_item.rejected_at.isoformat()
            if updated_item.rejected_at
            else None,
        }

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _generate_receiving_slip(
        self,
        session,
        items: list,
        organization_id: UUID,
    ):
        """Generate a receiving slip from session items grouped by SKU+batch.

        Enforces QSeal parent capacity — rejects if scanned items exceed capacity.
        """
        from app.models.qseal import QSealParameters, QSealTrack
        from app.services.document_numbering_service import DocumentNumberingService

        # ── QSeal capacity enforcement ────────────────────────────────────────
        all_batches = [item.batch_number for item in items if item.batch_number]
        if all_batches:
            params = (
                self.db.query(QSealParameters)
                .filter(
                    QSealParameters.serial_number.in_(all_batches),
                    QSealParameters.organization_id == organization_id,
                )
                .all()
            )
            param_by_serial = {p.serial_number: p for p in params if p.parent_id}

            if param_by_serial:
                parent_ids = list({p.parent_id for p in param_by_serial.values()})
                tracks = (
                    self.db.query(QSealTrack)
                    .filter(QSealTrack.id.in_(parent_ids))
                    .all()
                )
                track_by_id = {t.id: t for t in tracks}

                # Count items per parent
                parent_counts: dict = {}
                for item in items:
                    qsp = param_by_serial.get(item.batch_number)
                    if qsp and qsp.parent_id:
                        parent_counts[qsp.parent_id] = (
                            parent_counts.get(qsp.parent_id, 0) + 1
                        )

                for parent_id, count in parent_counts.items():
                    track = track_by_id.get(parent_id)
                    if track and track.capacity and count > track.capacity:
                        raise HTTPException(
                            status_code=422,
                            detail=(
                                f"QSeal parent '{track.name}' ({track.serial_number}) "
                                f"capacity exceeded: {count} items scanned, max {track.capacity}"
                            ),
                        )

        # ── Generate unique slip number ───────────────────────────────────────
        slip_number = DocumentNumberingService(self.db).get_next_number(
            organization_id, "receiving_slip"
        )

        # Aggregate items by SKU + batch
        sku_batch_agg: dict[tuple[str, str], dict] = defaultdict(
            lambda: {"quantity": 0, "box_count": 0}
        )
        for item in items:
            key = (item.sku, item.batch_number)
            sku_batch_agg[key]["quantity"] += item.raw_quantity
            sku_batch_agg[key]["box_count"] += 1

        total_boxes = len(items)
        total_items = sum(agg["quantity"] for agg in sku_batch_agg.values())

        # Override total_boxes with distinct QSeal parent count
        # Each unique master carton = 1 box, individual child items = items
        parent_boxes = self._count_distinct_qseal_parents(items, organization_id)
        if parent_boxes > 0:
            total_boxes = parent_boxes
            # total_items stays as the count of individual child items scanned

        # Create the receiving slip
        slip_data = {
            "organization_id": organization_id,
            "slip_number": slip_number,
            "session_id": session.id,
            "warehouse_id": session.warehouse_id,
            "asn_order_id": session.asn_order_id,
            "status": "pending_review",
            "total_boxes": total_boxes,
            "total_items": total_items,
        }
        slip = self.slip_repo.create(slip_data)

        # Add line items grouped by SKU + batch
        for (sku, batch), agg in sku_batch_agg.items():
            item_data = {
                "organization_id": organization_id,
                "sku": sku,
                "batch_number": batch,
                "quantity": agg["quantity"],
                "box_count": agg["box_count"],
                "flag": "ok",
            }
            self.slip_repo.add_item(slip.id, item_data)

        # Refresh to load items relationship
        self.db.refresh(slip)
        return slip

    def _session_to_dict(self, session) -> dict:
        """Convert a ScanSession model to a dictionary."""
        asn_order_no = None
        if session.asn_order_id and hasattr(session, "asn_order") and session.asn_order:
            asn_order_no = session.asn_order.asn_order_no

        return {
            "id": str(session.id),
            "organization_id": str(session.organization_id),
            "session_type": session.session_type,
            "worker_id": str(session.worker_id),
            "warehouse_id": str(session.warehouse_id),
            "dock_location": session.dock_location,
            "asn_order_id": str(session.asn_order_id) if session.asn_order_id else None,
            "asn_order_no": asn_order_no,
            "status": session.status,
            "total_boxes_scanned": session.total_boxes_scanned or 0,
            "started_at": session.started_at.isoformat()
            if session.started_at
            else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "created_at": session.created_at.isoformat()
            if session.created_at
            else None,
        }

    def _slip_base_dict(self, slip, groups: list) -> dict:
        """Convert a ReceivingSlip to a plain dict without QSeal enrichment."""
        asn_order_no = None
        if slip.asn_order_id and hasattr(slip, "asn_order") and slip.asn_order:
            asn_order_no = slip.asn_order.asn_order_no

        return {
            "id": str(slip.id),
            "organization_id": str(slip.organization_id),
            "slip_number": slip.slip_number,
            "session_id": str(slip.session_id),
            "warehouse_id": str(slip.warehouse_id),
            "asn_order_id": str(slip.asn_order_id) if slip.asn_order_id else None,
            "asn_order_no": asn_order_no,
            "status": slip.status,
            "total_boxes": slip.total_boxes,
            "total_items": slip.total_items,
            "rejection_reason": slip.rejection_reason,
            "notes": slip.notes,
            "groups": groups,
            "created_at": slip.created_at.isoformat() if slip.created_at else None,
            "updated_at": slip.updated_at.isoformat() if slip.updated_at else None,
        }

    # ------------------------------------------------------------------
    # COUNT DISTINCT QSEAL PARENT CONTAINERS
    # ------------------------------------------------------------------

    def _count_distinct_qseal_parents(self, items: list, organization_id: UUID) -> int:
        """Count unique QSeal parent containers from scanned items.

        Each master carton (QSeal parent) = 1 box.
        Items without a QSeal parent are each counted as 1 box (standalone).
        Items that share the same parent_id are grouped into 1 box.

        Args:
            items: List of ScanSessionItem objects.
            organization_id: Organization UUID.

        Returns:
            Number of distinct QSeal parent containers.
        """
        from app.models.qseal import QSealParameters

        batch_numbers = [item.batch_number for item in items if item.batch_number]
        if not batch_numbers:
            return len(items)

        # Fetch QSeal parent info for all batch numbers
        params = (
            self.db.query(QSealParameters)
            .filter(
                QSealParameters.serial_number.in_(batch_numbers),
                QSealParameters.organization_id == organization_id,
            )
            .all()
        )
        param_by_serial = {p.serial_number: p for p in params}

        parent_ids: set = set()
        standalone_count = 0

        for item in items:
            qsp = param_by_serial.get(item.batch_number)
            if qsp and qsp.parent_id:
                parent_ids.add(str(qsp.parent_id))
            else:
                standalone_count += 1

        return len(parent_ids) + standalone_count

    # ------------------------------------------------------------------
    # SLIP TO DICT
    # ------------------------------------------------------------------

    def _slip_to_dict(self, slip) -> dict:
        """Convert a ReceivingSlip model to a dictionary, enriched with QSeal parent/child data.

        Items sharing the same QSeal parent are grouped together.
        Children are shown once per parent group (not duplicated per item).
        """
        from app.models.qr_product import QRProduct
        from app.models.qseal import QSealParameters, QSealTrack

        if not slip.items:
            return self._slip_base_dict(slip, [])

        # Pre-load all QSeal data for performance
        all_batches = [item.batch_number for item in slip.items if item.batch_number]

        qseal_params_map = {}
        product_ids = set()
        if all_batches:
            params = (
                self.db.query(QSealParameters)
                .filter(
                    QSealParameters.serial_number.in_(all_batches),
                    QSealParameters.organization_id == slip.organization_id,
                )
                .all()
            )
            for p in params:
                qseal_params_map[p.serial_number] = p
                if p.product_id:
                    product_ids.add(p.product_id)

        # Pre-load products for names
        product_map = {}
        if product_ids:
            products = (
                self.db.query(QRProduct).filter(QRProduct.id.in_(product_ids)).all()
            )
            for prod in products:
                product_map[prod.id] = prod.name

        # Pre-load parent QSealTracks
        parent_ids = list(
            {p.parent_id for p in qseal_params_map.values() if p.parent_id}
        )
        qseal_track_map = {}
        if parent_ids:
            tracks = (
                self.db.query(QSealTrack).filter(QSealTrack.id.in_(parent_ids)).all()
            )
            for t in tracks:
                qseal_track_map[t.id] = t

        # Pre-load children per parent
        parent_children_map: dict = {}
        for pid in parent_ids:
            children = (
                self.db.query(QSealParameters)
                .filter(
                    QSealParameters.parent_id == pid,
                    QSealParameters.organization_id == slip.organization_id,
                )
                .all()
            )
            parent_children_map[pid] = [
                {
                    "id": str(c.id),
                    "serial_number": c.serial_number,
                    "dispatch_batch": c.dispatch_batch,
                    "manufacturing_date": str(c.manufacturing_date)
                    if c.manufacturing_date
                    else None,
                    "expiry_date": str(c.expiry_date) if c.expiry_date else None,
                }
                for c in children
            ]

        # Build lookup: serial_number → child detail (for merging into items)
        child_detail_map = {}
        for pid, children in parent_children_map.items():
            for c in children:
                child_detail_map[c["serial_number"]] = {
                    "manufacturing_date": c.get("manufacturing_date"),
                    "expiry_date": c.get("expiry_date"),
                }

        # Group items by QSeal parent
        groups: dict = {}
        for item in slip.items:
            qsp = qseal_params_map.get(item.batch_number)
            parent_key = str(qsp.parent_id) if (qsp and qsp.parent_id) else "__none__"

            if parent_key not in groups:
                parent_info = None
                if qsp and qsp.parent_id and qsp.parent_id in qseal_track_map:
                    parent = qseal_track_map[qsp.parent_id]
                    parent_info = {
                        "id": str(parent.id),
                        "serial_number": parent.serial_number,
                        "name": parent.name,
                        "qseal_type": parent.qseal_type,
                        "capacity": parent.capacity,
                    }

                groups[parent_key] = {
                    "parent_qseal": parent_info,
                    "product_name": product_map.get(qsp.product_id)
                    if qsp and qsp.product_id
                    else None,
                    "items": [],
                }

            # Merge ReceivingSlipItem + QSeal child detail into single item
            child_detail = child_detail_map.get(item.batch_number, {})
            groups[parent_key]["items"].append(
                {
                    "id": str(item.id),
                    "serial_number": item.batch_number,
                    "sku": item.sku,
                    "batch_number": item.batch_number,
                    "manufacturing_date": child_detail.get("manufacturing_date"),
                    "expiry_date": child_detail.get("expiry_date"),
                    "quantity": item.quantity,
                    "box_count": item.box_count,
                    "flag": item.flag,
                    "notes": item.notes,
                }
            )

        # Build grouped slip items for response
        grouped_items = list(groups.values())

        return {
            "id": str(slip.id),
            "organization_id": str(slip.organization_id),
            "slip_number": slip.slip_number,
            "session_id": str(slip.session_id),
            "warehouse_id": str(slip.warehouse_id),
            "status": slip.status,
            "total_boxes": slip.total_boxes,
            "total_items": slip.total_items,
            "rejection_reason": slip.rejection_reason,
            "notes": slip.notes,
            "groups": grouped_items,
            "created_at": slip.created_at.isoformat() if slip.created_at else None,
            "updated_at": slip.updated_at.isoformat() if slip.updated_at else None,
        }
