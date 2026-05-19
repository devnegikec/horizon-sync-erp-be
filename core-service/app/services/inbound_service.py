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

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.qr_scan_event import QRScanEvent
from app.repositories.receiving_slip_repository import ReceivingSlipRepository
from app.repositories.scan_session_repository import ScanSessionRepository
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
    ) -> dict:
        """
        Create a new inbound scan session with status OPEN.

        Args:
            worker_id: UUID of the dock worker starting the session.
            organization_id: Organization UUID for tenant isolation.
            warehouse_id: UUID of the warehouse where receiving occurs.
            dock_location: Optional dock location identifier.

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

        # Decode QR payload (raises ValidationError if invalid)
        payload = decode_qr_payload(qr_data)

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

        # Add scan session item
        item_data = {
            "organization_id": organization_id,
            "qr_identifier": payload.id,
            "sku": payload.sku,
            "quantity": payload.qty,
            "batch_number": payload.batch,
            "raw_qr_data": qr_data,
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
            "quantity": payload.qty,
            "batch_number": payload.batch,
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
            sku_batch_agg[key]["quantity"] += item.quantity
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
        total_quantity = sum(item.quantity for item in items)

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
        transitioning. After transitioning, triggers put-away list
        generation via PutAwayService and creates a worker task via
        TaskService if a worker_id is provided.

        Args:
            slip_id: UUID of the receiving slip to approve.
            organization_id: Organization UUID for tenant isolation.
            worker_id: Optional UUID of the worker to assign the put-away task to.

        Returns:
            Dictionary representation of the updated ReceivingSlip.

        Raises:
            NotFoundError: If slip is not found.
            StateError: If slip is not in PENDING_REVIEW status.

        Requirements: 7.1, 7.3, 8.1
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

        updated_slip = self.slip_repo.update_status(slip_id, "pending_putaway")
        self.db.refresh(updated_slip)

        # Trigger put-away list generation (with optional worker assignment)
        from app.services.put_away_service import PutAwayService

        put_away_service = PutAwayService(self.db)
        put_away_service.generate_from_slip(
            slip_id, organization_id, worker_id=worker_id
        )

        self.db.refresh(updated_slip)
        return self._slip_to_dict(updated_slip)

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
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _generate_receiving_slip(
        self,
        session,
        items: list,
        organization_id: UUID,
    ):
        """Generate a receiving slip from session items grouped by SKU+batch."""
        from app.services.document_numbering_service import DocumentNumberingService

        # Generate unique slip number
        slip_number = DocumentNumberingService(self.db).get_next_number(
            organization_id, "receiving_slip"
        )

        # Aggregate items by SKU + batch
        sku_batch_agg: dict[tuple[str, str], dict] = defaultdict(
            lambda: {"quantity": 0, "box_count": 0}
        )
        for item in items:
            key = (item.sku, item.batch_number)
            sku_batch_agg[key]["quantity"] += item.quantity
            sku_batch_agg[key]["box_count"] += 1

        total_boxes = len(items)
        total_items = sum(agg["quantity"] for agg in sku_batch_agg.values())

        # Create the receiving slip
        slip_data = {
            "organization_id": organization_id,
            "slip_number": slip_number,
            "session_id": session.id,
            "warehouse_id": session.warehouse_id,
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
        return {
            "id": str(session.id),
            "organization_id": str(session.organization_id),
            "session_type": session.session_type,
            "worker_id": str(session.worker_id),
            "warehouse_id": str(session.warehouse_id),
            "dock_location": session.dock_location,
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

    def _slip_to_dict(self, slip) -> dict:
        """Convert a ReceivingSlip model to a dictionary."""
        slip_items = []
        if slip.items:
            for item in slip.items:
                slip_items.append(
                    {
                        "id": str(item.id),
                        "sku": item.sku,
                        "batch_number": item.batch_number,
                        "quantity": item.quantity,
                        "box_count": item.box_count,
                        "flag": item.flag,
                        "notes": item.notes,
                    }
                )

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
            "items": slip_items,
            "created_at": slip.created_at.isoformat() if slip.created_at else None,
            "updated_at": slip.updated_at.isoformat() if slip.updated_at else None,
        }
