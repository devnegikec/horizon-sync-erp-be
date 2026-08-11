"""Repository for QSeal module"""

import uuid
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.qr_scan_event import QRScanEvent
from app.models.qseal import QSealTrack


class QSealRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Node CRUD ─────────────────────────────────────────────────────────────

    def create_node(self, data: dict) -> QSealTrack:
        node = QSealTrack(**data)
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        return node

    def get_by_id(self, node_id: UUID, organization_id: UUID) -> QSealTrack | None:
        return (
            self.db.query(QSealTrack)
            .filter(
                QSealTrack.id == node_id,
                QSealTrack.organization_id == organization_id,
            )
            .first()
        )

    def get_by_serial(
        self, serial_number: str, organization_id: UUID
    ) -> QSealTrack | None:
        return (
            self.db.query(QSealTrack)
            .filter(
                QSealTrack.serial_number == serial_number,
                QSealTrack.organization_id == organization_id,
            )
            .first()
        )

    def list_roots(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        qseal_type: str | None = None,
    ) -> tuple[list[QSealTrack], int]:
        """List top-level (parent_id IS NULL) nodes."""
        q = self.db.query(QSealTrack).filter(
            QSealTrack.organization_id == organization_id,
            QSealTrack.parent_id.is_(None),
        )
        if qseal_type:
            q = q.filter(QSealTrack.qseal_type == qseal_type)
        total = q.count()
        items = (
            q.order_by(QSealTrack.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def list_children(
        self,
        parent_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[QSealTrack], int]:
        q = self.db.query(QSealTrack).filter(
            QSealTrack.parent_id == parent_id,
            QSealTrack.organization_id == organization_id,
        )
        total = q.count()
        items = (
            q.order_by(QSealTrack.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def count_children(self, parent_id: UUID) -> int:
        return (
            self.db.query(func.count(QSealTrack.id))
            .filter(QSealTrack.parent_id == parent_id)
            .scalar()
        ) or 0

    def map_children(
        self, parent_id: UUID, child_ids: list[UUID], organization_id: UUID
    ) -> int:
        """Attach child nodes (QSealTrack or QSealParameters) to a parent.

        Handles both:
        - QSealTrack children (other cascade nodes): updates parent_id
        - QSealParameters children (ProductItem units): updates parent_id

        Allows re-assigning already-mapped children to a new parent.
        Returns count of successfully mapped children.
        """
        import logging

        logger = logging.getLogger(__name__)

        from app.models.qseal import QSealParameters

        mapped = 0
        for child_id in child_ids:
            # Try QSealTrack first
            child = self.get_by_id(child_id, organization_id)
            if child:
                if child.parent_id and child.parent_id != parent_id:
                    logger.info(
                        "[QSEAL] map_children re-assigning track id=%s from parent=%s to parent=%s",
                        child_id,
                        child.parent_id,
                        parent_id,
                    )
                child.parent_id = parent_id
                mapped += 1
                continue

            # Try QSealParameters (individual units from ProductItems)
            child_param = (
                self.db.query(QSealParameters)
                .filter(
                    QSealParameters.id == child_id,
                    QSealParameters.organization_id == organization_id,
                )
                .first()
            )
            if child_param:
                old_parent = child_param.parent_id
                if old_parent and old_parent != parent_id:
                    logger.info(
                        "[QSEAL] map_children re-assigning param id=%s serial=%s from parent=%s to parent=%s",
                        child_id,
                        child_param.serial_number,
                        old_parent,
                        parent_id,
                    )
                child_param.parent_id = parent_id
                mapped += 1
                continue

            logger.warning(
                "[QSEAL] map_children child not found id=%s org=%s",
                child_id,
                organization_id,
            )

        self.db.commit()
        logger.info(
            "[QSEAL] map_children parent=%s total_requested=%d mapped=%d",
            parent_id,
            len(child_ids),
            mapped,
        )
        return mapped

    def generate_serial(self, prefix: str = "QSL") -> str:
        """Generate a short unique serial for a QSeal node (max 10 chars)."""
        return f"{prefix}{str(uuid.uuid4()).replace('-', '')[:7].upper()}"

    # ── Scan History ──────────────────────────────────────────────────────────

    def record_scan(self, data: dict) -> QRScanEvent:
        event = QRScanEvent(**data)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_scan_history(
        self,
        organization_id: UUID,
        serial_number: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[QRScanEvent], int]:
        q = self.db.query(QRScanEvent).filter(
            QRScanEvent.organization_id == organization_id
        )
        if serial_number:
            q = q.filter(QRScanEvent.serial_number == serial_number)
        total = q.count()
        items = (
            q.order_by(QRScanEvent.scan_timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total
