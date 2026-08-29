"""Repository for scan session and scan session item database operations."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.scan_session import ScanSession, ScanSessionItem


class ScanSessionRepository:
    """Repository for scan session CRUD and query operations."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # CREATE SESSION
    # ------------------------------------------------------------------

    def create_session(self, data: dict) -> ScanSession:
        """
        Create a new scan session.

        Args:
            data: Dictionary containing session fields
                  (organization_id, session_type, worker_id, warehouse_id, etc.).

        Returns:
            Created ScanSession object.
        """
        session = ScanSession(**data)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    # ------------------------------------------------------------------
    # GET BY ID
    # ------------------------------------------------------------------

    def get_by_id(self, session_id: UUID, org_id: UUID) -> ScanSession | None:
        """
        Get a scan session by ID scoped to an organization.

        Args:
            session_id: The scan session UUID.
            org_id: Organization UUID for tenant isolation.

        Returns:
            ScanSession or None if not found.
        """
        return (
            self.db.query(ScanSession)
            .filter(
                ScanSession.id == session_id,
                ScanSession.organization_id == org_id,
            )
            .first()
        )

    # ------------------------------------------------------------------
    # ADD ITEM
    # ------------------------------------------------------------------

    def add_item(self, session_id: UUID, item_data: dict) -> ScanSessionItem:
        """
        Add a scan item to a session.

        Args:
            session_id: The scan session UUID.
            item_data: Dictionary containing item fields
                       (organization_id, qr_identifier, sku, quantity,
                        batch_number, raw_qr_data).

        Returns:
            Created ScanSessionItem object.
        """
        item = ScanSessionItem(session_id=session_id, **item_data)
        self.db.add(item)

        # Increment total_boxes_scanned on the session
        session = (
            self.db.query(ScanSession).filter(ScanSession.id == session_id).first()
        )
        if session:
            session.total_boxes_scanned = (session.total_boxes_scanned or 0) + 1

        self.db.commit()
        self.db.refresh(item)
        return item

    # ------------------------------------------------------------------
    # GET ITEMS
    # ------------------------------------------------------------------

    def get_items(self, session_id: UUID) -> list[ScanSessionItem]:
        """
        Get all items in a scan session.

        Args:
            session_id: The scan session UUID.

        Returns:
            List of ScanSessionItem objects ordered by scanned_at.
        """
        return (
            self.db.query(ScanSessionItem)
            .filter(ScanSessionItem.session_id == session_id)
            .order_by(ScanSessionItem.scanned_at)
            .all()
        )

    # ------------------------------------------------------------------
    # CLOSE SESSION
    # ------------------------------------------------------------------

    def close_session(self, session_id: UUID) -> ScanSession | None:
        """
        Close a scan session by setting status to 'closed' and recording
        the end timestamp.

        Args:
            session_id: The scan session UUID.

        Returns:
            Updated ScanSession or None if not found.
        """
        session = (
            self.db.query(ScanSession).filter(ScanSession.id == session_id).first()
        )
        if session is None:
            return None

        session.status = "closed"
        session.ended_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(session)
        return session

    # ------------------------------------------------------------------
    # CANCEL SESSION
    # ------------------------------------------------------------------

    def cancel_session(self, session_id: UUID) -> ScanSession | None:
        """
        Cancel a scan session by setting status to 'cancelled' and recording
        the end timestamp.

        Unlike close_session, cancelling does NOT generate a receiving slip —
        any scanned items are discarded and the ASN is released for a fresh
        session.

        Args:
            session_id: The scan session UUID.

        Returns:
            Updated ScanSession or None if not found.
        """
        session = (
            self.db.query(ScanSession).filter(ScanSession.id == session_id).first()
        )
        if session is None:
            return None

        session.status = "cancelled"
        session.ended_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(session)
        return session

    # ------------------------------------------------------------------
    # SET ASN ORDER
    # ------------------------------------------------------------------

    def set_asn_order(self, session_id: UUID, asn_order_id: UUID) -> ScanSession | None:
        """
        Link a scan session to an ASN order.

        Args:
            session_id: The scan session UUID.
            asn_order_id: The ASN order UUID to link.

        Returns:
            Updated ScanSession or None if not found.
        """
        session = (
            self.db.query(ScanSession).filter(ScanSession.id == session_id).first()
        )
        if session is None:
            return None

        session.asn_order_id = asn_order_id
        self.db.commit()
        self.db.refresh(session)
        return session

    # ------------------------------------------------------------------
    # LIST SESSIONS (filtered + paginated)
    # ------------------------------------------------------------------

    def list_sessions(
        self,
        org_id: UUID,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ScanSession], int]:
        """
        List scan sessions with optional filters and pagination.

        Args:
            org_id: Organization UUID for tenant isolation.
            filters: Optional dict with keys:
                - warehouse_id: UUID
                - worker_id: UUID
                - session_type: str (inbound, gate)
                - status: str (open, closed)
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Tuple of (list of sessions, total count).
        """
        query = self.db.query(ScanSession).filter(
            ScanSession.organization_id == org_id,
        )

        if filters:
            if filters.get("warehouse_id"):
                query = query.filter(
                    ScanSession.warehouse_id == filters["warehouse_id"]
                )
            if filters.get("worker_id"):
                query = query.filter(ScanSession.worker_id == filters["worker_id"])
            if filters.get("session_type"):
                query = query.filter(
                    ScanSession.session_type == filters["session_type"]
                )
            if filters.get("status"):
                query = query.filter(ScanSession.status == filters["status"])

        total = query.count()

        offset = (page - 1) * page_size
        sessions = (
            query.order_by(ScanSession.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return sessions, total
