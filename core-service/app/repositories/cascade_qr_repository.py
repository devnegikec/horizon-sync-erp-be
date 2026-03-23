"""Repository for Cascade / Hierarchical QR module"""

import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.qr_activation import QRActivationTrack
from app.models.qr_scan_event import QRScanEvent


class CascadeQRRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Node CRUD ─────────────────────────────────────────────────────────────

    def create_node(self, data: dict) -> QRActivationTrack:
        node = QRActivationTrack(**data)
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        return node

    def get_by_id(self, node_id: UUID, organization_id: UUID) -> QRActivationTrack | None:
        return (
            self.db.query(QRActivationTrack)
            .filter(
                QRActivationTrack.id == node_id,
                QRActivationTrack.organization_id == organization_id,
            )
            .first()
        )

    def get_by_serial(self, serial_number: str, organization_id: UUID) -> QRActivationTrack | None:
        return (
            self.db.query(QRActivationTrack)
            .filter(
                QRActivationTrack.serial_number == serial_number,
                QRActivationTrack.organization_id == organization_id,
            )
            .first()
        )

    def list_roots(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        qr_type: str | None = None,
    ) -> tuple[list[QRActivationTrack], int]:
        """List top-level (parent_id IS NULL) nodes."""
        q = self.db.query(QRActivationTrack).filter(
            QRActivationTrack.organization_id == organization_id,
            QRActivationTrack.parent_id.is_(None),
        )
        if qr_type:
            q = q.filter(QRActivationTrack.qr_type == qr_type)
        total = q.count()
        items = (
            q.order_by(QRActivationTrack.created_at.desc())
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
    ) -> tuple[list[QRActivationTrack], int]:
        q = self.db.query(QRActivationTrack).filter(
            QRActivationTrack.parent_id == parent_id,
            QRActivationTrack.organization_id == organization_id,
        )
        total = q.count()
        items = (
            q.order_by(QRActivationTrack.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def count_children(self, parent_id: UUID) -> int:
        return (
            self.db.query(func.count(QRActivationTrack.id))
            .filter(QRActivationTrack.parent_id == parent_id)
            .scalar()
        ) or 0

    def map_children(self, parent_id: UUID, child_ids: list[UUID], organization_id: UUID) -> int:
        """Attach child nodes to a parent. Returns count of successfully mapped nodes."""
        mapped = 0
        for child_id in child_ids:
            child = self.get_by_id(child_id, organization_id)
            if child and child.parent_id is None:  # only unattached children
                child.parent_id = parent_id
                mapped += 1
        self.db.commit()
        return mapped

    def generate_serial(self, prefix: str = "QR") -> str:
        """Generate a short unique serial for a cascade node."""
        return f"{prefix}{str(uuid.uuid4()).replace('-', '')[:8].upper()}"

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
