"""Repository for Analytics module"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import Date, cast, func
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
            q.with_entities(
                func.count(func.distinct(QRScanEvent.serial_number))
            ).scalar()
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
        by_device = [
            {"device_type": r.device_type, "count": r.count} for r in by_device_rows
        ]

        return {
            "total_scans": total_scans,
            "unique_serials": unique_serials,
            "by_date": by_date,
            "by_country": by_country,
            "by_device": by_device,
        }

    def get_interaction_funnel(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        q = self._base_query(organization_id, date_from, date_to)
        total_scans = q.count()

        # cta_action column may not exist yet in DB — default to 0
        try:
            scans_with_cta = q.filter(QRScanEvent.cta_action.is_not(None)).count()
        except Exception:
            scans_with_cta = 0

        from app.models.qr_scan_interaction import QRScanInteraction

        total_interactions = 0
        conversion_rate = 0.0
        top_interaction_types = []
        try:
            si_q = self.db.query(QRScanInteraction).filter(
                QRScanInteraction.organization_id == organization_id
            )
            if date_from:
                si_q = si_q.filter(QRScanInteraction.created_at >= date_from)
            if date_to:
                si_q = si_q.filter(QRScanInteraction.created_at <= date_to)
            total_interactions = si_q.count()

            conversion_rate = (
                round(scans_with_cta / total_scans * 100, 1) if total_scans else 0.0
            )

            top_types = (
                si_q.with_entities(
                    QRScanInteraction.interaction_type,
                    func.count().label("count"),
                )
                .group_by(QRScanInteraction.interaction_type)
                .order_by(func.count().desc())
                .limit(5)
                .all()
            )
            top_interaction_types = [
                {"type": r.interaction_type, "count": r.count} for r in top_types
            ]
        except Exception:
            pass

        scans_with_interactions = scans_with_cta

        return {
            "total_scans": total_scans,
            "scans_with_cta": scans_with_cta,
            "scans_with_interactions": scans_with_interactions,
            "total_interactions": total_interactions,
            "conversion_rate": conversion_rate,
            "top_interaction_types": top_interaction_types,
        }

    def get_cta_breakdown(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        try:
            q = self._base_query(organization_id, date_from, date_to)
            cta_rows = (
                q.with_entities(
                    QRScanEvent.cta_action,
                    func.count().label("count"),
                )
                .filter(QRScanEvent.cta_action.is_not(None))
                .group_by(QRScanEvent.cta_action)
                .order_by(func.count().desc())
                .all()
            )
            breakdown = [
                {"cta_action": r.cta_action or "Unknown", "count": r.count}
                for r in cta_rows
            ]
            total_scans_with_cta = sum(r.count for r in cta_rows)
            return {
                "breakdown": breakdown,
                "total_scans_with_cta": total_scans_with_cta,
            }
        except Exception:
            return {"breakdown": [], "total_scans_with_cta": 0}

    def get_geo_heatmap(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 500,
    ) -> dict:
        q = self._base_query(organization_id, date_from, date_to)
        q = q.filter(QRScanEvent.latitude.is_not(None))
        rows = (
            q.with_entities(
                QRScanEvent.latitude,
                QRScanEvent.longitude,
                QRScanEvent.city,
                QRScanEvent.state,
                QRScanEvent.country,
                func.count().label("count"),
            )
            .group_by(
                QRScanEvent.latitude,
                QRScanEvent.longitude,
                QRScanEvent.city,
                QRScanEvent.state,
                QRScanEvent.country,
            )
            .order_by(func.count().desc())
            .limit(limit)
            .all()
        )
        points = [
            {
                "city": r.city,
                "state": r.state,
                "country": r.country,
                "latitude": float(r.latitude) if r.latitude else 0,
                "longitude": float(r.longitude) if r.longitude else 0,
                "count": r.count,
            }
            for r in rows
        ]
        return {"points": points}

    def get_device_timeline(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        q = self._base_query(organization_id, date_from, date_to)
        rows = (
            q.with_entities(
                cast(QRScanEvent.scan_timestamp, Date).label("date"),
                QRScanEvent.device_type,
                func.count().label("count"),
            )
            .group_by(cast(QRScanEvent.scan_timestamp, Date), QRScanEvent.device_type)
            .order_by(cast(QRScanEvent.scan_timestamp, Date))
            .all()
        )
        timeline_map: dict = {}
        for r in rows:
            date_str = str(r.date)
            if date_str not in timeline_map:
                timeline_map[date_str] = {
                    "date": date_str,
                    "mobile": 0,
                    "desktop": 0,
                    "tablet": 0,
                    "unknown": 0,
                }
            dtype = (r.device_type or "unknown").lower()
            if dtype not in ("mobile", "desktop", "tablet"):
                dtype = "unknown"
            timeline_map[date_str][dtype] += r.count
        timeline = sorted(timeline_map.values(), key=lambda x: x["date"])
        return {"timeline": timeline}

    def _base_query(self, organization_id: UUID, date_from=None, date_to=None):
        q = self.db.query(QRScanEvent).filter(
            QRScanEvent.organization_id == organization_id
        )
        if date_from:
            q = q.filter(QRScanEvent.scan_timestamp >= date_from)
        if date_to:
            q = q.filter(QRScanEvent.scan_timestamp <= date_to)
        return q


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


class ScanInteractionRepository:
    """Placeholder for scan interaction tracking (Phase 4)."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict):
        logger = logging.getLogger(__name__)
        logger.warning(
            "ScanInteractionRepository.create called but model not yet available"
        )
        return None

    def list_by_scan(self, scan_event_id: UUID, organization_id: UUID):
        return []


class CTAConfigRepository:
    """Placeholder for CTA configuration (Phase 4)."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict):
        logger = logging.getLogger(__name__)
        logger.warning("CTAConfigRepository.create called but model not yet available")
        return None

    def list_by_product(self, organization_id: UUID, product_id: UUID):
        return []
