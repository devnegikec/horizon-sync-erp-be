"""Scanned Item Tracking Service — gate functions and stock entry logic."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.scanned_item_tracking import ScannedItemTracking

logger = logging.getLogger(__name__)


class ScannedItemTrackingService:
    """Manages the dual-axis state machine for receiving & put-away."""

    def __init__(self, db: Session):
        self.db = db

    # ── Gate Functions ────────────────────────────────────────────────────

    def can_scan(self, qr_identifier: str, session_id: UUID) -> bool:
        """Check if this QR has already been scanned in this session."""
        exists = (
            self.db.query(ScannedItemTracking)
            .filter(
                ScannedItemTracking.qr_identifier == qr_identifier,
                ScannedItemTracking.scan_session_id == session_id,
            )
            .first()
        )
        return exists is None

    def can_put_away(self, qr_identifier: str) -> tuple[bool, str | None]:
        """Check if an item is ready for put-away.

        Returns (allowed, error_message).
        """
        tracking = (
            self.db.query(ScannedItemTracking)
            .filter(ScannedItemTracking.qr_identifier == qr_identifier)
            .first()
        )
        if not tracking:
            return False, "Not scanned yet — scan first"
        if tracking.putaway_status == "completed":
            return False, "Already put away"
        if tracking.receiving_status == "rejected":
            return False, "Rejected by admin — cannot put away"
        return True, None

    def can_approve(self, tracking: ScannedItemTracking) -> tuple[bool, str | None]:
        """Check if an item can be approved by admin.

        Returns (allowed, error_message).
        """
        if tracking.receiving_status == "approved":
            return False, "Already approved"
        if tracking.receiving_status == "rejected":
            return False, "Already rejected"
        return True, None

    # ── Tracking Creation ─────────────────────────────────────────────────

    def create_from_scan(
        self,
        *,
        organization_id: UUID,
        warehouse_id: UUID,
        session_id: UUID,
        scan_item_id: UUID,
        qr_identifier: str,
        item_id: UUID,
        sku: str,
        quantity: int = 1,
        batch_number: str | None = None,
        scanned_by: UUID | None = None,
    ) -> ScannedItemTracking:
        """Create a tracking record when an item is scanned."""
        tracking = ScannedItemTracking(
            organization_id=organization_id,
            warehouse_id=warehouse_id,
            scan_session_id=session_id,
            scan_session_item_id=scan_item_id,
            qr_identifier=qr_identifier,
            item_id=item_id,
            sku=sku,
            batch_number=batch_number,
            quantity=quantity,
            receiving_status="scanned",
            putaway_status="pending",
            stock_entered=False,
            scanned_by=scanned_by,
        )
        self.db.add(tracking)
        self.db.flush()
        logger.info(
            "Tracking created: qr=%s session=%s item=%s",
            qr_identifier,
            session_id,
            scan_item_id,
        )
        return tracking

    # ── Standalone Scan (Direct Put-Away) ────────────────────────────────

    def resolve_item_from_payload(self, payload, organization_id: UUID):
        """Resolve the inventory Item for a decoded QR payload.

        - Unit/serial scans: resolve via ProductItem → QRProduct → Item.qr_product_id.
        - JSON box labels: fall back to SKU / GTIN / item_code matching.
        """
        from sqlalchemy import or_

        from app.models.item import Item
        from app.models.product_item import ProductItem

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
            if item is not None:
                return item

        return (
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

    def ensure_tracking_from_qr(
        self,
        qr_data: str,
        organization_id: UUID,
        warehouse_id: UUID,
        scanned_by: UUID | None = None,
    ) -> ScannedItemTracking:
        """Decode a QR and return an existing or newly-created tracking row.

        Used by Direct Put-Away when no inbound scan has created the row yet.
        """
        from app.services.qr_decoder import decode_qr_payload

        payload = decode_qr_payload(qr_data, db=self.db)

        existing = self.get_by_qr(payload.id)
        if existing is not None:
            return existing

        item = self.resolve_item_from_payload(payload, organization_id)
        if item is None:
            raise ValueError(
                f"No Item found for QR id='{payload.id}' sku='{payload.sku}'"
            )

        tracking = ScannedItemTracking(
            organization_id=organization_id,
            warehouse_id=warehouse_id,
            scan_session_id=None,
            scan_session_item_id=None,
            qr_identifier=payload.id,
            item_id=item.id,
            sku=item.sku or item.item_code or payload.sku,
            batch_number=payload.batch,
            quantity=payload.qty or 1,
            receiving_status="scanned",
            putaway_status="pending",
            stock_entered=False,
            scanned_by=scanned_by,
        )
        self.db.add(tracking)
        self.db.commit()
        logger.info(
            "Standalone tracking created (direct put-away): qr=%s item=%s",
            payload.id,
            item.id,
        )
        return tracking

    # ── Receiving Axis ────────────────────────────────────────────────────

    def approve_items(self, slip_id: UUID, approved_by: UUID) -> int:
        """Approve all scanned items on a receiving slip. Returns count of stock entries."""
        # Update receiving axis for scanned items
        updated = (
            self.db.query(ScannedItemTracking)
            .filter(
                ScannedItemTracking.receiving_slip_id == slip_id,
                ScannedItemTracking.receiving_status == "scanned",
            )
            .update(
                {
                    "receiving_status": "approved",
                    "received_at": datetime.now(UTC),
                    "received_by": approved_by,
                },
                synchronize_session="fetch",
            )
        )
        self.db.flush()

        # Enter stock for items where put-away is also complete
        ready = (
            self.db.query(ScannedItemTracking)
            .filter(
                ScannedItemTracking.receiving_slip_id == slip_id,
                ScannedItemTracking.receiving_status == "approved",
                ScannedItemTracking.putaway_status == "completed",
                ScannedItemTracking.stock_entered == False,  # noqa: E712
            )
            .all()
        )

        for t in ready:
            self._enter_stock(t)

        self.db.commit()
        logger.info(
            "Slip %s approved: %d items approved, %d entered stock",
            slip_id,
            updated,
            len(ready),
        )
        return len(ready)

    def reject_items(self, slip_id: UUID, reason: str, rejected_by: UUID) -> int:
        """Reject scanned items on a slip. Items already binned get retrieval tasks."""
        trackings = (
            self.db.query(ScannedItemTracking)
            .filter(
                ScannedItemTracking.receiving_slip_id == slip_id,
                ScannedItemTracking.receiving_status == "scanned",
            )
            .with_for_update()
            .all()
        )

        retrieval_count = 0
        for t in trackings:
            t.receiving_status = "rejected"
            t.rejection_reason = reason

            if t.putaway_status == "completed":
                # Item is physically in bin — create notification for retrieval
                retrieval_count += 1
                self._notify_retrieval_needed(t, reason)
                logger.warning(
                    "Item %s rejected after put-away — retrieval needed from bin %s",
                    t.qr_identifier,
                    t.bin_location_id,
                )

        self.db.commit()
        logger.info(
            "Slip %s rejected: %d items rejected, %d need retrieval",
            slip_id,
            len(trackings),
            retrieval_count,
        )
        return len(trackings)

    # ── Put-Away Axis ─────────────────────────────────────────────────────

    def complete_putaway(
        self,
        qr_identifier: str,
        bin_location_id: UUID,
        putaway_by: UUID,
        put_away_list_id: UUID | None = None,
        put_away_item_id: UUID | None = None,
    ) -> ScannedItemTracking:
        """Complete put-away for an item. Tries to enter stock if receiving is also done."""
        tracking = (
            self.db.query(ScannedItemTracking)
            .filter(ScannedItemTracking.qr_identifier == qr_identifier)
            .with_for_update()
            .first()
        )

        if not tracking:
            raise ValueError(f"No tracking found for QR: {qr_identifier}")

        ok, err = self.can_put_away(qr_identifier)
        if not ok:
            raise ValueError(err)

        tracking.putaway_status = "completed"
        tracking.bin_location_id = bin_location_id
        tracking.putaway_at = datetime.now(UTC)
        tracking.putaway_by = putaway_by
        tracking.put_away_list_id = put_away_list_id
        tracking.put_away_item_id = put_away_item_id
        self.db.flush()

        # Check if stock should enter now
        if self._should_enter_stock(tracking):
            self._enter_stock(tracking)

        self.db.commit()
        logger.info("Put-away completed: qr=%s bin=%s", qr_identifier, bin_location_id)
        return tracking

    def get_available_for_putaway(
        self, warehouse_id: UUID
    ) -> list[ScannedItemTracking]:
        """Get items scanned but not yet put away."""
        return (
            self.db.query(ScannedItemTracking)
            .filter(
                ScannedItemTracking.warehouse_id == warehouse_id,
                ScannedItemTracking.putaway_status == "pending",
                ScannedItemTracking.receiving_status.in_(["scanned", "approved"]),
            )
            .order_by(ScannedItemTracking.created_at)
            .all()
        )

    # ── Stock Entry ───────────────────────────────────────────────────────

    def _should_enter_stock(self, tracking: ScannedItemTracking) -> bool:
        """Stock enters only when BOTH receiving AND put-away are complete."""
        return (
            tracking.receiving_status == "approved"
            and tracking.putaway_status == "completed"
            and not tracking.stock_entered
        )

    def _enter_stock(self, tracking: ScannedItemTracking) -> None:
        """Enter stock into bin and update stock levels. Idempotent."""
        if tracking.stock_entered:
            return

        from app.services.bin_stock_service import BinStockService

        BinStockService(self.db).add_stock(
            bin_id=tracking.bin_location_id,
            item_id=tracking.item_id,
            quantity=tracking.quantity,
            org_id=tracking.organization_id,
            batch_number=tracking.batch_number,
        )

        tracking.stock_entered = True
        tracking.stock_entered_at = datetime.now(UTC)
        logger.info(
            "Stock entered: qr=%s item=%s qty=%d bin=%s",
            tracking.qr_identifier,
            tracking.item_id,
            tracking.quantity,
            tracking.bin_location_id,
        )

    def approve_tracking_row(
        self, tracking: ScannedItemTracking, approved_by: UUID | None = None
    ) -> bool:
        """Approve the receiving axis for a single tracking row.

        Used when a receiving slip is reconciled with items that were already
        put away via direct put-away. Once both axes are complete, stock is
        entered (idempotent via the stock_entered flag).

        Returns True if stock was entered.
        """
        if tracking.receiving_status == "scanned":
            tracking.receiving_status = "approved"
            tracking.received_at = datetime.now(UTC)
            tracking.received_by = approved_by

        if self._should_enter_stock(tracking):
            self._enter_stock(tracking)
            return True
        return False

    # ── Queries ───────────────────────────────────────────────────────────

    def get_by_qr(self, qr_identifier: str) -> ScannedItemTracking | None:
        return (
            self.db.query(ScannedItemTracking)
            .filter(ScannedItemTracking.qr_identifier == qr_identifier)
            .first()
        )

    def get_slip_summary(self, slip_id: UUID) -> list[dict]:
        """Group tracking records by receiving_status × putaway_status."""
        from sqlalchemy import func

        rows = (
            self.db.query(
                ScannedItemTracking.receiving_status,
                ScannedItemTracking.putaway_status,
                ScannedItemTracking.stock_entered,
                func.count().label("count"),
                func.sum(ScannedItemTracking.quantity).label("total_qty"),
            )
            .filter(ScannedItemTracking.receiving_slip_id == slip_id)
            .group_by(
                ScannedItemTracking.receiving_status,
                ScannedItemTracking.putaway_status,
                ScannedItemTracking.stock_entered,
            )
            .all()
        )

        return [
            {
                "receiving_status": r.receiving_status,
                "putaway_status": r.putaway_status,
                "stock_entered": r.stock_entered,
                "count": r.count,
                "total_qty": r.total_qty or 0,
            }
            for r in rows
        ]

    # ── Retrieval Notifications ────────────────────────────────────────────

    def _notify_retrieval_needed(
        self, tracking: ScannedItemTracking, reason: str
    ) -> None:
        """Create a notification when an item needs retrieval after rejection."""
        try:
            from app.models.notification import Notification

            notification = Notification(
                organization_id=tracking.organization_id,
                user_id=tracking.scanned_by,  # Notify the worker who scanned it
                type="retrieval_needed",
                title="Item Retrieval Required",
                message=(
                    f"Item {tracking.qr_identifier} (SKU: {tracking.sku}) "
                    f"was rejected after put-away. "
                    f"Retrieve from bin {tracking.bin_location_id}. "
                    f"Reason: {reason}"
                ),
                entity_type="scanned_item_tracking",
                entity_id=tracking.id,
                entity_no=tracking.qr_identifier,
                warehouse_id=tracking.warehouse_id,
                extra_data={
                    "qr_identifier": tracking.qr_identifier,
                    "bin_location_id": str(tracking.bin_location_id)
                    if tracking.bin_location_id
                    else None,
                    "rejection_reason": reason,
                },
            )
            self.db.add(notification)
            self.db.flush()
        except Exception:
            logger.warning(
                "Failed to create retrieval notification for %s", tracking.qr_identifier
            )
