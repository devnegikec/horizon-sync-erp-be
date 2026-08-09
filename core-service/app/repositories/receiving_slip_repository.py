"""Repository for receiving slip and receiving slip item database operations."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.receiving_slip import ReceivingSlip, ReceivingSlipItem


class ReceivingSlipRepository:
    """Repository for receiving slip CRUD and query operations."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create(self, data: dict) -> ReceivingSlip:
        """
        Create a new receiving slip.

        Args:
            data: Dictionary containing slip fields
                  (organization_id, slip_number, session_id, warehouse_id,
                   status, total_boxes, total_items, etc.).

        Returns:
            Created ReceivingSlip object.
        """
        slip = ReceivingSlip(**data)
        self.db.add(slip)
        self.db.commit()
        self.db.refresh(slip)
        return slip

    # ------------------------------------------------------------------
    # GET BY ID
    # ------------------------------------------------------------------

    def get_by_id(self, slip_id: UUID, org_id: UUID) -> ReceivingSlip | None:
        """
        Get a receiving slip by ID scoped to an organization.

        Args:
            slip_id: The receiving slip UUID.
            org_id: Organization UUID for tenant isolation.

        Returns:
            ReceivingSlip or None if not found.
        """
        return (
            self.db.query(ReceivingSlip)
            .filter(
                ReceivingSlip.id == slip_id,
                ReceivingSlip.organization_id == org_id,
            )
            .first()
        )

    # ------------------------------------------------------------------
    # UPDATE STATUS
    # ------------------------------------------------------------------

    def update_status(self, slip_id: UUID, status: str) -> ReceivingSlip | None:
        """
        Update the status of a receiving slip.

        Args:
            slip_id: The receiving slip UUID.
            status: New status value (e.g., pending_review, pending_putaway,
                    rejected, putaway_complete).

        Returns:
            Updated ReceivingSlip or None if not found.
        """
        slip = self.db.query(ReceivingSlip).filter(ReceivingSlip.id == slip_id).first()
        if slip is None:
            return None

        slip.status = status
        self.db.commit()
        self.db.refresh(slip)
        return slip

    # ------------------------------------------------------------------
    # ADD ITEM
    # ------------------------------------------------------------------

    def add_item(self, slip_id: UUID, item_data: dict) -> ReceivingSlipItem:
        """
        Add a line item to a receiving slip.

        Args:
            slip_id: The receiving slip UUID.
            item_data: Dictionary containing item fields
                       (organization_id, sku, batch_number, quantity,
                        box_count, flag, notes).

        Returns:
            Created ReceivingSlipItem object.
        """
        item = ReceivingSlipItem(slip_id=slip_id, **item_data)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    # ------------------------------------------------------------------
    # GET ITEMS
    # ------------------------------------------------------------------

    def get_items(self, slip_id: UUID) -> list[ReceivingSlipItem]:
        """
        Get all line items for a receiving slip.

        Args:
            slip_id: The receiving slip UUID.

        Returns:
            List of ReceivingSlipItem objects ordered by creation time.
        """
        return (
            self.db.query(ReceivingSlipItem)
            .filter(ReceivingSlipItem.slip_id == slip_id)
            .order_by(ReceivingSlipItem.created_at)
            .all()
        )

    # ------------------------------------------------------------------
    # GET ITEM BY ID
    # ------------------------------------------------------------------

    def get_item_by_id(self, item_id: UUID, org_id: UUID) -> ReceivingSlipItem | None:
        """
        Get a receiving slip item by ID scoped to an organization.

        Args:
            item_id: The receiving slip item UUID.
            org_id: Organization UUID for tenant isolation.

        Returns:
            ReceivingSlipItem or None if not found.
        """
        return (
            self.db.query(ReceivingSlipItem)
            .filter(
                ReceivingSlipItem.id == item_id,
                ReceivingSlipItem.organization_id == org_id,
            )
            .first()
        )

    # ------------------------------------------------------------------
    # UPDATE ITEM FLAG
    # ------------------------------------------------------------------

    def update_item_flag(
        self, item_id: UUID, flag: str, notes: str | None = None
    ) -> ReceivingSlipItem | None:
        """
        Update the flag and notes on a receiving slip item.

        Args:
            item_id: The receiving slip item UUID.
            flag: New flag value (ok, short, damaged, rejected).
            notes: Optional notes about the flag.

        Returns:
            Updated ReceivingSlipItem or None if not found.
        """
        item = (
            self.db.query(ReceivingSlipItem)
            .filter(ReceivingSlipItem.id == item_id)
            .first()
        )
        if item is None:
            return None

        item.flag = flag
        if notes is not None:
            item.notes = notes
        self.db.commit()
        self.db.refresh(item)
        return item

    # ------------------------------------------------------------------
    # REJECT ITEM
    # ------------------------------------------------------------------

    def reject_item(
        self,
        item_id: UUID,
        reason: str,
        rejected_by: UUID | None = None,
        notes: str | None = None,
    ) -> ReceivingSlipItem | None:
        """
        Mark a receiving slip item as rejected with a reason.

        Args:
            item_id: The receiving slip item UUID.
            reason: Rejection reason text.
            rejected_by: UUID of the user rejecting the item.
            notes: Optional additional notes.

        Returns:
            Updated ReceivingSlipItem or None if not found.
        """
        item = (
            self.db.query(ReceivingSlipItem)
            .filter(ReceivingSlipItem.id == item_id)
            .first()
        )
        if item is None:
            return None

        from datetime import UTC, datetime

        item.flag = "rejected"
        item.rejection_reason = reason
        item.rejected_by = rejected_by
        item.rejected_at = datetime.now(UTC)
        if notes is not None:
            item.notes = notes
        self.db.commit()
        self.db.refresh(item)
        return item

    # ------------------------------------------------------------------
    # GET ITEMS BY SLIP ID (for ASN mismatch queries)
    # ------------------------------------------------------------------

    def get_items_by_slip_id(self, slip_id: UUID) -> list[ReceivingSlipItem]:
        """
        Get all line items for a receiving slip (alias for get_items).

        Args:
            slip_id: The receiving slip UUID.

        Returns:
            List of ReceivingSlipItem objects.
        """
        return self.get_items(slip_id)

    # ------------------------------------------------------------------
    # GET SLIPS BY ASN ORDER
    # ------------------------------------------------------------------

    def get_slips_by_asn_order(
        self, asn_order_id: UUID, org_id: UUID
    ) -> list[ReceivingSlip]:
        """
        Get all receiving slips linked to an ASN order.

        Args:
            asn_order_id: The ASN order UUID.
            org_id: Organization UUID for tenant isolation.

        Returns:
            List of ReceivingSlip objects.
        """
        return (
            self.db.query(ReceivingSlip)
            .options(joinedload(ReceivingSlip.asn_order))
            .filter(
                ReceivingSlip.asn_order_id == asn_order_id,
                ReceivingSlip.organization_id == org_id,
            )
            .order_by(ReceivingSlip.created_at.asc())
            .all()
        )

    # ------------------------------------------------------------------
    # UPDATE REJECTION REASON
    # ------------------------------------------------------------------

    def update_rejection_reason(
        self, slip_id: UUID, reason: str
    ) -> ReceivingSlip | None:
        """
        Update the rejection reason on a receiving slip.

        Args:
            slip_id: The receiving slip UUID.
            reason: Rejection reason text.

        Returns:
            Updated ReceivingSlip or None if not found.
        """
        slip = self.db.query(ReceivingSlip).filter(ReceivingSlip.id == slip_id).first()
        if slip is None:
            return None

        slip.rejection_reason = reason
        slip.status = "rejected"
        self.db.commit()
        self.db.refresh(slip)
        return slip

    # ------------------------------------------------------------------
    # LIST SLIPS (filtered + paginated)
    # ------------------------------------------------------------------

    def list_slips(
        self,
        org_id: UUID,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ReceivingSlip], int]:
        """
        List receiving slips with optional filters and pagination.

        Args:
            org_id: Organization UUID for tenant isolation.
            filters: Optional dict with keys:
                - warehouse_id: UUID
                - session_id: UUID
                - status: str (pending_review, pending_putaway, rejected,
                               putaway_complete)
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Tuple of (list of slips, total count).
        """
        query = (
            self.db.query(ReceivingSlip)
            .options(
                joinedload(ReceivingSlip.asn_order),
            )
            .filter(
                ReceivingSlip.organization_id == org_id,
            )
        )

        if filters:
            if filters.get("warehouse_id"):
                query = query.filter(
                    ReceivingSlip.warehouse_id == filters["warehouse_id"]
                )
            if filters.get("session_id"):
                query = query.filter(ReceivingSlip.session_id == filters["session_id"])
            if filters.get("status"):
                query = query.filter(ReceivingSlip.status == filters["status"])

        total = query.count()

        offset = (page - 1) * page_size
        slips = (
            query.order_by(ReceivingSlip.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return slips, total
