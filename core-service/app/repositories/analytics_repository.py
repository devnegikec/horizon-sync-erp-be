"""Repository for Analytics module"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Date, cast, func, or_
from sqlalchemy.orm import Session

from app.models.analytics import MetaCampaign
from app.models.qr_cta_config import QRCTAConfig
from app.models.qr_product import QRProduct
from app.models.qr_scan_event import QRScanEvent
from app.models.qr_scan_interaction import QRScanInteraction


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

        scans_with_cta = q.filter(QRScanEvent.cta_action.is_not(None)).count()

        # Scope interactions to the same scan cohort as the date-filtered scan
        # query. This avoids counting actions belonging to another tenant or to
        # scans outside the requested reporting period.
        scan_ids = q.with_entities(QRScanEvent.id)
        si_q = self.db.query(QRScanInteraction).filter(
            QRScanInteraction.organization_id == organization_id,
            QRScanInteraction.scan_event_id.in_(scan_ids),
        )
        total_interactions = si_q.count()
        scans_with_interactions = (
            si_q.with_entities(
                func.count(func.distinct(QRScanInteraction.scan_event_id))
            ).scalar()
            or 0
        )
        conversion_rate = (
            round(scans_with_interactions / total_scans * 100, 1)
            if total_scans
            else 0.0
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
            {"type": row.interaction_type, "count": row.count} for row in top_types
        ]

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
        q = q.filter(
            QRScanEvent.latitude.is_not(None),
            QRScanEvent.longitude.is_not(None),
            QRScanEvent.latitude.between(-90, 90),
            QRScanEvent.longitude.between(-180, 180),
        )
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
                "latitude": float(r.latitude),
                "longitude": float(r.longitude),
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
    """Persistence for tenant-scoped post-scan interactions."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict):
        scan = (
            self.db.query(QRScanEvent)
            .filter(
                QRScanEvent.organization_id == data["organization_id"],
                or_(
                    QRScanEvent.id == data["scan_event_id"],
                    QRScanEvent.event_id == data["scan_event_id"],
                ),
            )
            .first()
        )
        if scan is None:
            return None
        payload = {**data, "scan_event_id": scan.id}
        interaction = QRScanInteraction(**payload)
        self.db.add(interaction)
        self.db.commit()
        self.db.refresh(interaction)
        return interaction

    def list_by_scan(self, scan_event_id: UUID, organization_id: UUID):
        return (
            self.db.query(QRScanInteraction)
            .filter(
                QRScanInteraction.scan_event_id == scan_event_id,
                QRScanInteraction.organization_id == organization_id,
            )
            .order_by(QRScanInteraction.created_at.asc())
            .all()
        )


class CTAConfigRepository:
    """Persistence for product CTA configuration."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict):
        product_exists = (
            self.db.query(QRProduct.id)
            .filter(
                QRProduct.id == data["product_id"],
                QRProduct.organization_id == data["organization_id"],
                QRProduct.deleted_at.is_(None),
            )
            .first()
        )
        if product_exists is None:
            return None
        config = QRCTAConfig(**data)
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def list_by_product(self, organization_id: UUID, product_id: UUID):
        return (
            self.db.query(QRCTAConfig)
            .filter(
                QRCTAConfig.organization_id == organization_id,
                QRCTAConfig.product_id == product_id,
            )
            .order_by(QRCTAConfig.display_order.asc(), QRCTAConfig.created_at.asc())
            .all()
        )

    def get_by_id(self, config_id: UUID, organization_id: UUID):
        return (
            self.db.query(QRCTAConfig)
            .filter(
                QRCTAConfig.id == config_id,
                QRCTAConfig.organization_id == organization_id,
            )
            .first()
        )

    def update(self, config: QRCTAConfig, data: dict):
        for field, value in data.items():
            setattr(config, field, value)
        self.db.commit()
        self.db.refresh(config)
        return config

    def delete(self, config: QRCTAConfig) -> None:
        self.db.delete(config)
        self.db.commit()
