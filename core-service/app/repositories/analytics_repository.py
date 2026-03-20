"""Repository for Analytics module"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session

from app.models.analytics import MetaCampaign
from app.models.qr_scan_event import QRScanEvent


class QRScanEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> QRScanEvent:
        event = QRScanEvent(**data)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 50,
        serial_number: str | None = None,
        product_item_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[QRScanEvent], int]:
        q = self.db.query(QRScanEvent).filter(
            QRScanEvent.organization_id == organization_id
        )
        if serial_number:
            q = q.filter(QRScanEvent.serial_number == serial_number)
        if product_item_id:
            q = q.filter(QRScanEvent.product_item_id == product_item_id)
        if date_from:
            q = q.filter(QRScanEvent.scan_timestamp >= date_from)
        if date_to:
            q = q.filter(QRScanEvent.scan_timestamp <= date_to)
        total = q.count()
        items = (
            q.order_by(QRScanEvent.scan_timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_scan_analytics(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        serial_number: str | None = None,
    ) -> dict:
        q = self.db.query(QRScanEvent).filter(
            QRScanEvent.organization_id == organization_id
        )
        if serial_number:
            q = q.filter(QRScanEvent.serial_number == serial_number)
        if date_from:
            q = q.filter(QRScanEvent.scan_timestamp >= date_from)
        if date_to:
            q = q.filter(QRScanEvent.scan_timestamp <= date_to)

        total_scans = q.count()
        unique_serials = (
            q.with_entities(func.count(func.distinct(QRScanEvent.serial_number)))
            .scalar()
        ) or 0

        # Scans by date
        by_date_rows = (
            q.with_entities(
                cast(QRScanEvent.scan_timestamp, Date).label("date"),
                func.count().label("count"),
            )
            .group_by(cast(QRScanEvent.scan_timestamp, Date))
            .order_by(cast(QRScanEvent.scan_timestamp, Date))
            .all()
        )
        by_date = [{"date": str(r.date), "count": r.count} for r in by_date_rows]

        # Scans by country
        by_country_rows = (
            q.with_entities(
                QRScanEvent.country,
                func.count().label("count"),
            )
            .group_by(QRScanEvent.country)
            .order_by(func.count().desc())
            .limit(20)
            .all()
        )
        by_country = [{"country": r.country, "count": r.count} for r in by_country_rows]

        # Scans by device
        by_device_rows = (
            q.with_entities(
                QRScanEvent.device_type,
                func.count().label("count"),
            )
            .group_by(QRScanEvent.device_type)
            .order_by(func.count().desc())
            .all()
        )
        by_device = [{"device_type": r.device_type, "count": r.count} for r in by_device_rows]

        return {
            "total_scans": total_scans,
            "unique_serials": unique_serials,
            "by_date": by_date,
            "by_country": by_country,
            "by_device": by_device,
        }


class MetaCampaignRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> MetaCampaign:
        mc = MetaCampaign(**data)
        self.db.add(mc)
        self.db.commit()
        self.db.refresh(mc)
        return mc

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        campaign_id: str | None = None,
    ) -> tuple[list[MetaCampaign], int]:
        q = self.db.query(MetaCampaign).filter(
            MetaCampaign.organization_id == organization_id
        )
        if campaign_id:
            q = q.filter(MetaCampaign.campaign_id == campaign_id)
        total = q.count()
        items = (
            q.order_by(MetaCampaign.fetched_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_by_id(self, mc_id: UUID, organization_id: UUID) -> MetaCampaign | None:
        return (
            self.db.query(MetaCampaign)
            .filter(
                MetaCampaign.id == mc_id,
                MetaCampaign.organization_id == organization_id,
            )
            .first()
        )

    def upsert_snapshot(self, organization_id: UUID, data: dict) -> MetaCampaign:
        """Always inserts a new snapshot row (time-series approach)."""
        data["organization_id"] = organization_id
        return self.create(data)
