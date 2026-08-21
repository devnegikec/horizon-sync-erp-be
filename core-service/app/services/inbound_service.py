"""Inbound service for managing scan sessions, receiving slips, and QR decoding.

Handles the inbound receiving workflow:
- Start/end scan sessions for dock workers
- Record QR scans with duplicate detection
- Generate receiving slips from closed sessions
- Provide session summaries with per-SKU/batch aggregation

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 14.1
"""

import logging
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.item_packaging_unit import ItemPackagingUnit
from app.models.qr_scan_event import QRScanEvent
from app.models.receiving_slip import ReceivingSlipItem
from app.models.scan_session import ScanSessionItem
from app.models.scanned_item_tracking import ScannedItemTracking
from app.repositories.receiving_slip_repository import ReceivingSlipRepository
from app.repositories.scan_session_repository import ScanSessionRepository
from app.services.item_packaging_unit_service import ItemPackagingUnitService
from app.services.qr_decoder import decode_qr_payload

logger = logging.getLogger(__name__)


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
        # ── Guard against duplicate sessions/slips for the same ASN ──
        if asn_order_id:
            from app.models.receiving_slip import ReceivingSlip
            from app.models.scan_session import ScanSession

            existing_open = (
                self.db.query(ScanSession)
                .filter(
                    ScanSession.organization_id == organization_id,
                    ScanSession.asn_order_id == asn_order_id,
                    ScanSession.status == "open",
                )
                .first()
            )
            if existing_open is not None:
                raise ValidationError(
                    message="An open scan session already exists for this ASN",
                    details=[
                        {
                            "field": "asn_order_id",
                            "reason": (
                                f"Session {existing_open.id} is already open for this ASN"
                            ),
                        }
                    ],
                )

            existing_slip = (
                self.db.query(ReceivingSlip)
                .filter(
                    ReceivingSlip.organization_id == organization_id,
                    ReceivingSlip.asn_order_id == asn_order_id,
                    ReceivingSlip.status != "rejected",
                )
                .first()
            )
            if existing_slip is not None:
                raise ValidationError(
                    message="A receiving slip already exists for this ASN",
                    details=[
                        {
                            "field": "asn_order_id",
                            "reason": (
                                f"Receiving slip {existing_slip.slip_number} already "
                                f"exists for this ASN"
                            ),
                        }
                    ],
                )

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

        # ── Resolve the inventory Item for this scan ──
        # - Unit/serial scans: payload.id is the ProductItem serial, so resolve
        #   the Item via ProductItem → QRProduct → Item.qr_product_id.
        # - JSON box labels: payload.sku is the real SKU, so fall back to
        #   SKU / GTIN / item_code matching.
        from app.models.item import Item
        from app.models.product_item import ProductItem

        item = None

        product_item = (
            self.db.query(ProductItem)
            .filter(
                ProductItem.serial_number == payload.id,
                ProductItem.organization_id == organization_id,
                ProductItem.deleted_at.is_(None),
            )
            .first()
        )
        if product_item is not None:
            item = (
                self.db.query(Item)
                .filter(
                    Item.qr_product_id == product_item.product_id,
                    Item.organization_id == organization_id,
                    Item.deleted_at.is_(None),
                )
                .first()
            )

        if item is None:
            item = (
                self.db.query(Item)
                .filter(
                    Item.organization_id == organization_id,
                    Item.deleted_at.is_(None),
                    or_(
                        Item.sku == payload.sku,
                        Item.gtin == payload.sku,
                        Item.item_code == payload.sku,
                    ),
                )
                .first()
            )

        # ── Validate scanned item against the linked ASN (when present) ──
        if session.asn_order_id:
            from app.models.asn_order import AsnOrder

            asn_order = (
                self.db.query(AsnOrder)
                .filter(
                    AsnOrder.id == session.asn_order_id,
                    AsnOrder.organization_id == organization_id,
                )
                .first()
            )
            if asn_order is None:
                raise ValidationError(
                    message="Linked ASN order not found",
                    details=[
                        {
                            "field": "asn_order_id",
                            "reason": f"ASN '{session.asn_order_id}' does not exist",
                        }
                    ],
                )

            asn_item_ids = {line.item_id for line in asn_order.items}
            asn_lookup_keys: set[str] = set()
            for line in asn_order.items:
                if not line.item:
                    continue
                for key in (line.item.sku, line.item.gtin, line.item.item_code):
                    if key:
                        asn_lookup_keys.add(key)

            matched = False
            if item is not None:
                if item.id in asn_item_ids:
                    matched = True
                else:
                    for key in (item.sku, item.gtin, item.item_code):
                        if key and key in asn_lookup_keys:
                            matched = True
                            break
            if not matched and payload.sku in asn_lookup_keys:
                matched = True

            if not matched:
                raise ValidationError(
                    message="Scanned item does not belong to the linked ASN",
                    details=[
                        {
                            "field": "qr_data",
                            "reason": (
                                f"Item '{payload.sku or payload.id}' is not part of "
                                f"ASN order {asn_order.asn_order_no}"
                            ),
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

        # ── NEW: Create scanned_item_tracking record (dual-axis handoff) ──
        # `item` was resolved above (and validated against the linked ASN).
        from app.services.scanned_item_tracking_service import (
            ScannedItemTrackingService,
        )

        if item is not None:
            tracking_svc = ScannedItemTrackingService(self.db)
            tracking_svc.create_from_scan(
                organization_id=organization_id,
                warehouse_id=session.warehouse_id,
                session_id=session_id,
                scan_item_id=scan_item.id,
                qr_identifier=payload.id,
                item_id=item.id,
                sku=item.sku or item.item_code or payload.sku,
                quantity=payload.qty or 1,
                batch_number=payload.batch,
                scanned_by=worker_id,
            )
        else:
            logger.warning(
                "No Item found for QR id='%s' sku='%s' in org=%s — tracking record skipped",
                payload.id,
                payload.sku,
                organization_id,
            )

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
        rejections: list[dict] | None = None,
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
            rejections=rejections,
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
        rejections: list[dict] | None = None,
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
            rejections=rejections,
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
        rejected_keys = {(r["sku"], r["batch_number"]) for r in rejected_items}

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
            if key in rejected_keys:
                # Already saved above — will be re-added as rejected below.
                continue
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

        # ── Approve tracking records for this slip ──
        from app.services.scanned_item_tracking_service import (
            ScannedItemTrackingService,
        )

        tracking_svc = ScannedItemTrackingService(self.db)
        # Link tracking records to this slip
        trackings_updated = (
            self.db.query(ScannedItemTracking)
            .filter(
                ScannedItemTracking.scan_session_id == slip.session_id,
                ScannedItemTracking.receiving_status == "scanned",
            )
            .update(
                {"receiving_slip_id": slip_id},
                synchronize_session="fetch",
            )
        )
        # Approve them — stock enters for items already binned
        stock_entered = tracking_svc.approve_items(slip_id, approved_by=worker_id)
        logger.info(
            "Tracking: %d records linked to slip %s, %d entered stock",
            trackings_updated,
            slip_id,
            stock_entered,
        )

        # ------------------------------------------------------------------
        # Step 4: Determine slip status after approval.
        # If every accepted item is already binned (direct put-away happened
        # before the slip was generated), go straight to PUTAWAY_COMPLETE and
        # skip generating a duplicate put-away list.
        # ------------------------------------------------------------------
        from app.services.put_away_service import PutAwayService

        put_away_service = PutAwayService(self.db)
        # approve_slip deletes and recreates receiving_slip_items (Step 3),
        # which resets put_away_status to "pending". Re-run reconciliation so
        # items already binned via direct put-away are linked again before we
        # decide the slip status.
        put_away_service.reconcile_slip_with_completed_putaway(slip, organization_id)

        if put_away_service.all_slip_items_put_away(slip_id):
            updated_slip = self.slip_repo.update_status(slip_id, "putaway_complete")
        else:
            updated_slip = self.slip_repo.update_status(slip_id, "pending_putaway")
            put_away_service.generate_from_slip(
                slip_id, organization_id, worker_id=worker_id
            )

        # ------------------------------------------------------------------
        # Step 5: Update ASN delivered_qty and status
        # _sync_asn_delivered_qty handles both delivered_qty per item AND
        # the overall ASN status (partially_delivered / delivered).
        # ------------------------------------------------------------------
        if slip.asn_order_id:
            self._sync_asn_delivered_qty(slip.asn_order_id, organization_id)

        # Step 6: Create a material_receipt stock entry for ERP traceability.
        self._create_receiving_stock_entry(slip, organization_id, worker_id)

        self.db.refresh(updated_slip)
        return self._slip_to_dict(updated_slip)

    # ------------------------------------------------------------------
    # RECEIVING STOCK ENTRY (ERP traceability)
    # ------------------------------------------------------------------

    def _create_receiving_stock_entry(
        self,
        slip,
        organization_id: UUID,
        user_id: UUID | None = None,
    ) -> None:
        """Create a submitted material_receipt stock entry for a receiving slip.

        Document-only record for ERP traceability. Bin and warehouse stock
        levels are already updated by the dual-axis flow, so stock levels are
        NOT re-applied here (avoids double counting).
        """
        from decimal import Decimal

        from app.models.item import Item
        from app.models.stock_entry import StockEntry
        from app.schemas.stock_entry import StockEntryCreate, StockEntryItemCreate
        from app.services.stock_entry_service import StockEntryService

        # Idempotency: one stock entry per receiving slip.
        existing = (
            self.db.query(StockEntry)
            .filter(
                StockEntry.organization_id == organization_id,
                StockEntry.reference_type == "receiving_slip",
                StockEntry.reference_id == slip.id,
            )
            .first()
        )
        if existing:
            logger.info(
                "Stock entry already exists for receiving slip %s (%s) — skipping.",
                slip.slip_number,
                existing.stock_entry_no,
            )
            return

        if not slip.warehouse_id:
            logger.warning(
                "Receiving slip %s has no warehouse; skipping stock entry.",
                slip.slip_number,
            )
            return

        # Fresh query of accepted slip items (approve_slip recreates them).
        slip_items = (
            self.db.query(ReceivingSlipItem)
            .filter(ReceivingSlipItem.slip_id == slip.id)
            .all()
        )

        resolved: list[tuple[UUID, Decimal, str | None, str | None]] = []
        for slip_item in slip_items:
            if slip_item.flag != "ok":
                continue
            item = (
                self.db.query(Item)
                .filter(
                    (
                        (Item.item_code == slip_item.sku)
                        | (Item.sku == slip_item.sku)
                        | (Item.gtin == slip_item.sku)
                    ),
                    Item.organization_id == organization_id,
                )
                .first()
            )
            if item is None:
                logger.warning(
                    "Receiving slip %s: no item matched for sku %s; skipping stock entry line.",
                    slip.slip_number,
                    slip_item.sku,
                )
                continue
            resolved.append(
                (
                    item.id,
                    Decimal(str(slip_item.quantity or 0)),
                    item.uom,
                    slip_item.batch_number,
                )
            )

        if not resolved:
            logger.warning(
                "Receiving slip %s has no resolvable accepted items; skipping stock entry.",
                slip.slip_number,
            )
            return

        items = [
            StockEntryItemCreate(
                item_id=item_id,
                qty=qty,
                uom=uom or "Nos",
                batch_no=batch,
            )
            for item_id, qty, uom, batch in resolved
        ]

        try:
            svc = StockEntryService(self.db)
            entry = svc.create(
                StockEntryCreate(
                    stock_entry_type="material_receipt",
                    to_warehouse_id=slip.warehouse_id,
                    posting_date=datetime.now(UTC),
                    status="submitted",
                    reference_type="receiving_slip",
                    reference_id=slip.id,
                    remarks=(
                        f"Auto-generated from receiving slip {slip.slip_number}"
                        + (f" (ASN {slip.asn_order_id})" if slip.asn_order_id else "")
                    ),
                    items=items,
                ),
                organization_id,
                user_id,  # type: ignore[arg-type]
            )
            # `create` already stores the entry as submitted; stamp the time.
            entry.submitted_at = datetime.now(UTC)
            self.db.commit()
            logger.info(
                "Created stock entry %s for receiving slip %s.",
                entry.stock_entry_no,
                slip.slip_number,
            )
        except Exception as exc:
            logger.error(
                "Failed to create stock entry for receiving slip %s: %s",
                slip.slip_number,
                exc,
                exc_info=True,
            )

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

        # Aggregate accepted qty per SKU across all slips (rejected/floating
        # items are NOT counted as delivered).
        delivered_by_sku = {}
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
            delivered_by_sku[sku] = int(total) if total else 0

        # Update each ASN item's delivered_qty
        all_delivered = True
        any_delivered = False
        for asn_item in asn_order.items:
            if not asn_item.item:
                continue
            delivered = 0
            # Receiving slip items may carry the SKU, GTIN, or item_code as the
            # identifier, so try all of them.
            for lookup_key in (
                asn_item.item.sku,
                asn_item.item.item_code,
                asn_item.item.gtin,
            ):
                if lookup_key:
                    delivered = delivered_by_sku.get(lookup_key, 0)
                    if delivered > 0:
                        break
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

    def _update_asn_status(self, asn_order_id: UUID, organization_id: UUID) -> None:
        """Update ASN status based on receiving slip approval progress.

        - First slip approved → partially_delivered
        - All expected items delivered → delivered
        - Otherwise → no change (already partially_delivered)
        """
        from app.models.asn_order import AsnOrder
        from app.models.receiving_slip import ReceivingSlip

        asn_order = (
            self.db.query(AsnOrder)
            .filter(
                AsnOrder.id == asn_order_id,
                AsnOrder.organization_id == organization_id,
            )
            .first()
        )
        if not asn_order:
            return

        # Count approved slips for this ASN
        approved_slips = (
            self.db.query(ReceivingSlip)
            .filter(
                ReceivingSlip.asn_order_id == asn_order_id,
                ReceivingSlip.organization_id == organization_id,
                ReceivingSlip.status.in_(["pending_putaway", "putaway_complete"]),
            )
            .count()
        )

        total_slips = (
            self.db.query(ReceivingSlip)
            .filter(
                ReceivingSlip.asn_order_id == asn_order_id,
                ReceivingSlip.organization_id == organization_id,
            )
            .count()
        )

        if approved_slips > 0 and asn_order.status == "confirmed":
            asn_order.status = "partially_delivered"
        elif approved_slips >= total_slips and total_slips > 0:
            asn_order.status = "delivered"

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

        # ── Update dual-axis tracking rows ──
        from app.services.scanned_item_tracking_service import (
            ScannedItemTrackingService,
        )

        tracking_service = ScannedItemTrackingService(self.db)
        tracking_service.reject_items(
            slip_id=slip_id,
            reason=reason.strip(),
            rejected_by=None,  # slip-level reject doesn't have rejected_by
        )

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

        # ── Update dual-axis tracking row ──
        # batch_number in receiving_slip_items stores the serial number (qr_identifier)
        # receiving_slip_id may not be set yet (only set during approve), so match by session
        from app.models.scanned_item_tracking import ScannedItemTracking

        tracking = (
            self.db.query(ScannedItemTracking)
            .filter(
                ScannedItemTracking.qr_identifier == updated_item.batch_number,
                ScannedItemTracking.scan_session_id == slip.session_id,
            )
            .first()
        )
        if tracking:
            tracking.receiving_status = "rejected"
            tracking.rejection_reason = reason.strip()
            if not tracking.receiving_slip_id:
                tracking.receiving_slip_id = slip_id
            self.db.commit()
            logger.info(
                "Tracking rejected: qr=%s slip=%s item=%s",
                updated_item.batch_number,
                slip_id,
                item_id,
            )
        else:
            logger.warning(
                "No tracking row found for rejected item: qr=%s session=%s",
                updated_item.batch_number,
                slip.session_id,
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

    def update_items_status(
        self,
        slip_id: UUID,
        items: list,
        organization_id: UUID,
        user_id: UUID | None = None,
    ) -> list[dict]:
        """Apply per-item status updates (rejected / ok / short / damaged).

        This is the bulk equivalent of calling the individual reject / flag
        endpoints — one request, one payload, with a per-item ``status``.
        """
        results: list[dict] = []
        for entry in items:
            status = entry.status
            if status == "rejected":
                results.append(
                    self.reject_slip_item(
                        slip_id=slip_id,
                        item_id=entry.item_id,
                        reason=entry.reason or "Rejected during review",
                        organization_id=organization_id,
                        rejected_by=user_id,
                        notes=entry.notes,
                    )
                )
            elif status in ("short", "damaged"):
                results.append(
                    self.flag_line_item(
                        slip_id=slip_id,
                        item_id=entry.item_id,
                        flag=status,
                        notes=entry.notes,
                        organization_id=organization_id,
                    )
                )
            elif status == "ok":
                results.append(
                    self.reset_slip_item(
                        slip_id=slip_id,
                        item_id=entry.item_id,
                        organization_id=organization_id,
                    )
                )
            else:
                raise ValidationError(
                    message=f"Invalid item status '{status}'",
                    details=[
                        {
                            "field": "items",
                            "reason": "status must be one of: rejected, ok, short, damaged",
                        }
                    ],
                )
        return results

    def reset_slip_item(
        self,
        slip_id: UUID,
        item_id: UUID,
        organization_id: UUID,
    ) -> dict:
        """Reset a receiving slip item back to 'ok' (undo a rejection/flag)."""
        slip = self.slip_repo.get_by_id(slip_id, organization_id)
        if slip is None:
            raise NotFoundError(
                message="Receiving slip not found",
                entity_type="ReceivingSlip",
                entity_id=str(slip_id),
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

        updated_item = self.slip_repo.update_item_flag(item_id, "ok", None)
        updated_item.rejection_reason = None
        updated_item.rejected_by = None
        updated_item.rejected_at = None
        self.db.commit()

        # Reset the dual-axis tracking row back to 'scanned'
        from app.models.scanned_item_tracking import ScannedItemTracking

        tracking = (
            self.db.query(ScannedItemTracking)
            .filter(
                ScannedItemTracking.qr_identifier == updated_item.batch_number,
                ScannedItemTracking.scan_session_id == slip.session_id,
            )
            .first()
        )
        if tracking:
            tracking.receiving_status = "scanned"
            tracking.rejection_reason = None
            self.db.commit()

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
            "rejected_at": None,
        }

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _apply_rejections(
        self,
        slip,
        session,
        organization_id: UUID,
        rejections: list[dict] | None,
    ) -> None:
        """Mark scanned units as rejected on the receiving slip + tracking rows.

        Applied at slip generation time so rejected items are excluded from
        put-away, stock entry, and ASN delivered qty. If the item was already
        put away via direct put-away, we deliberately do nothing else — the
        warehouse manager is alerted and resolves it manually.
        """
        if not rejections:
            return

        from app.models.receiving_slip import ReceivingSlipItem
        from app.models.scanned_item_tracking import ScannedItemTracking

        now = datetime.now(UTC)
        for rej in rejections:
            serial = str(rej.get("serial_number") or "").strip()
            if not serial:
                continue
            reason = str(rej.get("reason") or "Rejected during review").strip()

            slip_items = (
                self.db.query(ReceivingSlipItem)
                .filter(
                    ReceivingSlipItem.slip_id == slip.id,
                    ReceivingSlipItem.batch_number == serial,
                    ReceivingSlipItem.flag == "ok",
                )
                .all()
            )
            for item in slip_items:
                item.flag = "rejected"
                item.rejection_reason = reason
                item.rejected_at = now
                item.put_away_status = "pending"

            trackings = (
                self.db.query(ScannedItemTracking)
                .filter(
                    ScannedItemTracking.qr_identifier == serial,
                    ScannedItemTracking.scan_session_id == session.id,
                )
                .all()
            )
            for tracking in trackings:
                if tracking.receiving_status == "scanned":
                    tracking.receiving_status = "rejected"
                    tracking.rejection_reason = reason
                    tracking.receiving_slip_id = slip.id

        self.db.flush()

    def _generate_receiving_slip(
        self,
        session,
        items: list,
        organization_id: UUID,
        rejections: list[dict] | None = None,
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

        # Apply rejections before finalization (rejected items never enter
        # stock or put-away — they are left for the warehouse manager).
        self._apply_rejections(slip, session, organization_id, rejections)

        # Flow B: link items already put away via direct put-away (match by QR)
        from app.services.put_away_service import PutAwayService

        put_away_service = PutAwayService(self.db)
        put_away_service.reconcile_slip_with_completed_putaway(slip, organization_id)

        # ── Direct put-away already completed before receiving? ──
        # If every accepted item is already binned, skip the review/approve
        # cycle entirely: mark the slip PUTAWAY_COMPLETE and advance the ASN so
        # the flow ends at the expected terminal state immediately.
        if put_away_service.all_slip_items_put_away(slip.id):
            slip = self.slip_repo.update_status(slip.id, "putaway_complete")
            if slip is not None and slip.asn_order_id:
                self._sync_asn_delivered_qty(slip.asn_order_id, organization_id)
            # Create a material_receipt stock entry for ERP traceability.
            if slip is not None:
                self._create_receiving_stock_entry(slip, organization_id)

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
        # Fetch ASN info directly from DB — more reliable than lazy/eager-loaded relationships
        asn_order_id = str(slip.asn_order_id) if slip.asn_order_id else None
        asn_order_no = None
        if slip.asn_order_id:
            from app.models.asn_order import AsnOrder

            asn = (
                self.db.query(AsnOrder).filter(AsnOrder.id == slip.asn_order_id).first()
            )
            if asn:
                asn_order_no = asn.asn_order_no

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
                    "dispatch_batch": c.get("dispatch_batch"),  # real batch number
                }

        # Group items by QSeal parent
        groups: dict = {}
        for item in slip.items:
            qsp = qseal_params_map.get(item.batch_number)
            parent_key = str(qsp.parent_id) if (qsp and qsp.parent_id) else "__none__"

            if parent_key not in groups:
                parent_info = None
                parent_batch = None
                if qsp and qsp.parent_id and qsp.parent_id in qseal_track_map:
                    parent = qseal_track_map[qsp.parent_id]
                    parent_batch = parent.name  # QSealTrack.name = batch name
                    parent_info = {
                        "id": str(parent.id),
                        "serial_number": parent.serial_number,
                        "name": parent.name,
                        "batch": parent_batch,
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
            real_batch = child_detail.get("dispatch_batch") or item.batch_number
            groups[parent_key]["items"].append(
                {
                    "id": str(item.id),
                    "serial_number": item.batch_number,
                    "sku": item.sku,
                    "batch_number": real_batch,  # actual dispatch_batch, not serial
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

        # Fetch ASN info directly from DB — more reliable than lazy/eager-loaded relationships
        asn_order_id = str(slip.asn_order_id) if slip.asn_order_id else None
        asn_order_no = None
        if slip.asn_order_id:
            from app.models.asn_order import AsnOrder

            asn = (
                self.db.query(AsnOrder).filter(AsnOrder.id == slip.asn_order_id).first()
            )
            if asn:
                asn_order_no = asn.asn_order_no

        return {
            "id": str(slip.id),
            "organization_id": str(slip.organization_id),
            "slip_number": slip.slip_number,
            "session_id": str(slip.session_id),
            "warehouse_id": str(slip.warehouse_id),
            "asn_order_id": asn_order_id,
            "asn_order_no": asn_order_no,
            "status": slip.status,
            "total_boxes": slip.total_boxes,
            "total_items": slip.total_items,
            "rejection_reason": slip.rejection_reason,
            "notes": slip.notes,
            "groups": grouped_items,
            "created_at": slip.created_at.isoformat() if slip.created_at else None,
            "updated_at": slip.updated_at.isoformat() if slip.updated_at else None,
        }
