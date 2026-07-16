"""Repository for Analytics module"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Date, String, cast, func
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

    def get_cta_breakdown(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        q = self.db.query(QRScanEvent).filter(
            QRScanEvent.organization_id == organization_id
        )
        if date_from:
            q = q.filter(QRScanEvent.scan_timestamp >= date_from)
        if date_to:
            q = q.filter(QRScanEvent.scan_timestamp <= date_to)

        # Count scans that have cta_action in extra_data
        cta_action_expr = cast(QRScanEvent.extra_data["cta_action"], String)
        cta_q = q.filter(QRScanEvent.extra_data["cta_action"].isnot(None))
        total_scans_with_cta = cta_q.count()

        cta_rows = (
            cta_q.with_entities(
                cta_action_expr.label("cta_action"),
                func.count().label("count"),
            )
            .group_by(cta_action_expr)
            .order_by(func.count().desc())
            .all()
        )
        breakdown = [
            {"cta_action": (r.cta_action or "").strip('"'), "count": r.count}
            for r in cta_rows
        ]

        return {"breakdown": breakdown, "total_scans_with_cta": total_scans_with_cta}

    def get_geo_heatmap(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 500,
    ) -> list[dict]:
        q = self.db.query(QRScanEvent).filter(
            QRScanEvent.organization_id == organization_id,
            QRScanEvent.city.isnot(None),
        )
        if date_from:
            q = q.filter(QRScanEvent.scan_timestamp >= date_from)
        if date_to:
            q = q.filter(QRScanEvent.scan_timestamp <= date_to)

        rows = (
            q.with_entities(
                QRScanEvent.city,
                QRScanEvent.state,
                QRScanEvent.country,
                func.avg(QRScanEvent.latitude).label("latitude"),
                func.avg(QRScanEvent.longitude).label("longitude"),
                func.count().label("count"),
            )
            .group_by(QRScanEvent.city, QRScanEvent.state, QRScanEvent.country)
            .order_by(func.count().desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "city": r.city,
                "state": r.state,
                "country": r.country,
                "latitude": float(r.latitude) if r.latitude else None,
                "longitude": float(r.longitude) if r.longitude else None,
                "count": r.count,
            }
            for r in rows
        ]

    def get_device_timeline(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict]:
        q = self.db.query(QRScanEvent).filter(
            QRScanEvent.organization_id == organization_id
        )
        if date_from:
            q = q.filter(QRScanEvent.scan_timestamp >= date_from)
        if date_to:
            q = q.filter(QRScanEvent.scan_timestamp <= date_to)

        # Get all rows grouped by date and device_type
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

        # Pivot into {date, mobile, desktop, tablet, unknown}
        date_map: dict[str, dict] = {}
        for r in rows:
            d = str(r.date)
            if d not in date_map:
                date_map[d] = {
                    "date": d,
                    "mobile": 0,
                    "desktop": 0,
                    "tablet": 0,
                    "unknown": 0,
                }
            dt = (r.device_type or "unknown").lower()
            if dt in ("mobile", "desktop", "tablet"):
                date_map[d][dt] = r.count
            else:
                date_map[d]["unknown"] += r.count

        return sorted(date_map.values(), key=lambda x: x["date"])

    def get_interaction_funnel(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        q = self.db.query(QRScanEvent).filter(
            QRScanEvent.organization_id == organization_id
        )
        if date_from:
            q = q.filter(QRScanEvent.scan_timestamp >= date_from)
        if date_to:
            q = q.filter(QRScanEvent.scan_timestamp <= date_to)

        total_scans = q.count()

        # Scans with a CTA action
        cta_q = q.filter(QRScanEvent.extra_data["cta_action"].isnot(None))
        scans_with_cta = cta_q.count()

        # Scans with interactions (call, form_submit, share actions in extra_data)
        interaction_q = q.filter(QRScanEvent.extra_data["interaction_type"].isnot(None))
        scans_with_interactions = interaction_q.count()

        # Total interactions
        total_interactions = scans_with_interactions

        # Conversion rate
        conversion_rate = (
            round(scans_with_interactions / total_scans, 4) if total_scans > 0 else 0.0
        )

        # Top interaction types
        interaction_type_expr = cast(QRScanEvent.extra_data["interaction_type"], String)
        interaction_type_rows = (
            interaction_q.with_entities(
                interaction_type_expr.label("interaction_type"),
                func.count().label("count"),
            )
            .group_by(interaction_type_expr)
            .order_by(func.count().desc())
            .limit(10)
            .all()
        )
        top_interaction_types = [
            {"interaction_type": r.interaction_type, "count": r.count}
            for r in interaction_type_rows
        ]

        return {
            "total_scans": total_scans,
            "scans_with_cta": scans_with_cta,
            "scans_with_interactions": scans_with_interactions,
            "total_interactions": total_interactions,
            "conversion_rate": conversion_rate,
            "top_interaction_types": top_interaction_types,
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
