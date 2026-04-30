"""Repository for Cascade module"""

from uuid import UUID
import uuid

from sqlalchemy.orm import Session
from app.models.qr_activation import QRTypeEnum
from app.models.qr_activation import QRActivationParameters, QRActivationTrack

from app.models.product_item import ProductItem
from app.models.brand import Brand
from sqlalchemy import func

class QRActivationTrackRepository:
    def __init__(self, db: Session):
        self.db = db


    def create_node(self, data: dict) -> QRActivationTrack:
        node = QRActivationTrack(**data)
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        return node


    def create(self, data: dict) -> QRActivationTrack:
        track = QRActivationTrack(**data)
        self.db.add(track)
        self.db.commit()
        self.db.refresh(track)
        return track

    def get_by_id(
        self, track_id: UUID, organization_id: UUID
    ) -> QRActivationTrack | None:
        return (
            self.db.query(QRActivationTrack)
            .filter(
                QRActivationTrack.id == track_id,
                QRActivationTrack.organization_id == organization_id,
                QRActivationTrack.deleted_at.is_(None),
            )
            .first()
        )

    def get_by_serial(
        self, serial_number: str, organization_id: UUID
    ) -> QRActivationTrack | None:
        return (
            self.db.query(QRActivationTrack)
            .filter(
                QRActivationTrack.serial_number == serial_number,
                QRActivationTrack.organization_id == organization_id,
                QRActivationTrack.deleted_at.is_(None),
            )
            .first()
        )

    def list_roots(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[QRActivationTrack], int]:
        """List non-cascade-mapped tracks (app_cascade_map=False)"""
        q = self.db.query(QRActivationTrack).filter(
            QRActivationTrack.organization_id == organization_id,
           # QRActivationTrack.app_cascade_map.is_(False),
            QRActivationTrack.deleted_at.is_(None),
        )
        if search:
            q = q.filter(QRActivationTrack.qr_type == QRTypeEnum(search))
        total = q.count()
        items = (
            q.order_by(QRActivationTrack.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        print(f"list_roots: total={total} returned={len(items)}")
        return items, total
    
    def count_children(self, parent_app_id: UUID) -> int:
        track_count = (
            self.db.query(func.count(QRActivationTrack.id))
            .filter(QRActivationTrack.parent_app_id == parent_app_id)
            .scalar()
        ) or 0

        if track_count:
            return track_count

        param_count = (
            self.db.query(func.count(QRActivationParameters.id))
            .filter(QRActivationParameters.parent_app_id == parent_app_id)
            .scalar()
        ) or 0

        return param_count
    
    def list_history(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[QRActivationTrack], int]:
        """List cascade-mapped tracks (app_cascade_map=True)"""
        q = self.db.query(QRActivationTrack).filter(
            QRActivationTrack.organization_id == organization_id,
            QRActivationTrack.app_cascade_map.is_(True),
            QRActivationTrack.deleted_at.is_(None),
        )
        if search:
            q = q.filter(QRActivationTrack.qr_type == QRTypeEnum(search))
        total = q.count()
        items = (
            q.order_by(QRActivationTrack.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def update(
        self, track: QRActivationTrack, data: dict
    ) -> QRActivationTrack:
        for k, v in data.items():
            setattr(track, k, v)
        self.db.commit()
        self.db.refresh(track)
        return track

    def get_children_by_serials_and_type(
        self,
        serial_numbers: list[str],
        qr_type: str,
        organization_id: UUID,
    ) -> list[str]:
        """Return matching serial numbers filtered by qr_type"""
        rows = (
            self.db.query(QRActivationTrack.serial_number)
            .filter(
                QRActivationTrack.serial_number.in_(serial_numbers),
                QRActivationTrack.qr_type == qr_type,
                QRActivationTrack.organization_id == organization_id,
                QRActivationTrack.deleted_at.is_(None),
            )
            .all()
        )
        return [r.serial_number for r in rows]

    def map_children_to_parent(
        self,
        serial_numbers: list[str],
        parent_id: UUID,
        organization_id: UUID,
    ) -> None:
        """Set parent_app_id on all matching child tracks"""
        self.db.query(QRActivationTrack).filter(
            QRActivationTrack.serial_number.in_(serial_numbers),
            QRActivationTrack.organization_id == organization_id,
        ).update(
            {"parent_app_id": parent_id},
            synchronize_session=False,
        )

    def mark_cascade_mapped(self, track: QRActivationTrack) -> None:
        track.app_cascade_map = True
        self.db.flush()

    def generate_serial(self, prefix: str = "QR") -> str:
        """Generate a short unique serial for a cascade node."""
        return f"{prefix}{str(uuid.uuid4()).replace('-', '')[:8].upper()}"
    
    def get_brand(self, organization_id: UUID):
        return (
            self.db.query(Brand)
            .filter(
                Brand.organization_id == organization_id,
                Brand.deleted_at.is_(None)
            )
            .first()
        )


class CascadeActivationRepository:
    """Read-only access to QRActivationParameters for cascade lookups"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_serial(
        self, serial_number: str, organization_id: UUID
    ) -> QRActivationParameters | None:
        return (
            self.db.query(QRActivationParameters)
            .filter(
                QRActivationParameters.serial_number == serial_number,
                QRActivationParameters.organization_id == organization_id,
            )
            .first()
        )

    def get_children_by_serials(
        self, serial_numbers: list[str], organization_id: UUID
    ) -> list[str]:
        """Return matching serial numbers from activation params (shipper type)"""
        rows = (
            self.db.query(QRActivationParameters.serial_number)
            .filter(
                QRActivationParameters.serial_number.in_(serial_numbers),
                QRActivationParameters.organization_id == organization_id,
            )
            .all()
        )
        return [r.serial_number for r in rows]

    def map_children_to_parent(
        self,
        serial_numbers: list[str],
        parent_id: UUID,
        organization_id: UUID,
    ) -> None:
        """Set parent_app_id on activation params for shipper type"""
        self.db.query(QRActivationParameters).filter(
            QRActivationParameters.serial_number.in_(serial_numbers),
            QRActivationParameters.organization_id == organization_id,
        ).update(
            {"parent_app_id": parent_id},
            synchronize_session=False,
        )


class ProductItemCascadeRepository:
    """Read-only access to ProductItem for cascade scan validation"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_serial(
        self, serial_number: str, organization_id: UUID
    ) -> ProductItem | None:
        return (
            self.db.query(ProductItem)
            .filter(
                ProductItem.serial_number == serial_number,
                ProductItem.organization_id == organization_id,
                ProductItem.deleted_at.is_(None),
            )
            .first()
        )