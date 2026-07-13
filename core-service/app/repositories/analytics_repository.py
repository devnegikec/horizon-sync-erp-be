"""Repository for Analytics module"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session

from app.models.analytics import MetaCampaign
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

    # ── Phase 4: Enhanced Analytics ───────────────────────────────────────

    def get_cta_breakdown(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        q = self.db.query(
            QRScanEvent.cta_action,
            func.count().label("count"),
        ).filter(
            QRScanEvent.organization_id == organization_id,
            QRScanEvent.cta_action.isnot(None),
        )
        if date_from:
            q = q.filter(QRScanEvent.scan_timestamp >= date_from)
        if date_to:
            q = q.filter(QRScanEvent.scan_timestamp <= date_to)
        rows = q.group_by(QRScanEvent.cta_action).order_by(func.count().desc()).all()
        breakdown = [
            {"cta_action": r.cta_action or "unknown", "count": r.count} for r in rows
        ]
        total_with_cta = sum(r.count for r in rows)
        return {"breakdown": breakdown, "total_scans_with_cta": total_with_cta}

    def get_geo_heatmap(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 500,
    ) -> list[dict]:
        q = self.db.query(
            QRScanEvent.city,
            QRScanEvent.state,
            QRScanEvent.country,
            QRScanEvent.latitude,
            QRScanEvent.longitude,
            func.count().label("count"),
        ).filter(
            QRScanEvent.organization_id == organization_id,
            QRScanEvent.latitude.isnot(None),
        )
        if date_from:
            q = q.filter(QRScanEvent.scan_timestamp >= date_from)
        if date_to:
            q = q.filter(QRScanEvent.scan_timestamp <= date_to)
        rows = (
            q.group_by(
                QRScanEvent.city,
                QRScanEvent.state,
                QRScanEvent.country,
                QRScanEvent.latitude,
                QRScanEvent.longitude,
            )
            .order_by(func.count().desc())
            .limit(limit)
            .all()
        )
        return [
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

    def get_device_timeline(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict]:
        """Scans grouped by date + device_type (mobile/desktop/tablet/unknown)."""
        q = self.db.query(
            cast(QRScanEvent.scan_timestamp, Date).label("date"),
            QRScanEvent.device_type,
            func.count().label("count"),
        ).filter(QRScanEvent.organization_id == organization_id)
        if date_from:
            q = q.filter(QRScanEvent.scan_timestamp >= date_from)
        if date_to:
            q = q.filter(QRScanEvent.scan_timestamp <= date_to)
        rows = (
            q.group_by(
                cast(QRScanEvent.scan_timestamp, Date),
                QRScanEvent.device_type,
            )
            .order_by(cast(QRScanEvent.scan_timestamp, Date))
            .all()
        )
        # Pivot: date -> {mobile, desktop, tablet, unknown}
        date_map: dict[str, dict] = {}
        for r in rows:
            date_str = str(r.date)
            if date_str not in date_map:
                date_map[date_str] = {
                    "date": date_str,
                    "mobile": 0,
                    "desktop": 0,
                    "tablet": 0,
                    "unknown": 0,
                }
            dt = r.device_type or "unknown"
            if dt not in ("mobile", "desktop", "tablet"):
                dt = "unknown"
            date_map[date_str][dt] += r.count
        return list(date_map.values())

    def get_interaction_funnel(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        """Funnel: total scans -> with CTA -> with interactions."""
        scan_q = self.db.query(QRScanEvent).filter(
            QRScanEvent.organization_id == organization_id
        )
        if date_from:
            scan_q = scan_q.filter(QRScanEvent.scan_timestamp >= date_from)
        if date_to:
            scan_q = scan_q.filter(QRScanEvent.scan_timestamp <= date_to)

        total_scans = scan_q.count()
        scans_with_cta = scan_q.filter(QRScanEvent.cta_action.isnot(None)).count()

        # Scans that have at least one interaction
        scans_with_interactions = (
            self.db.query(func.count(func.distinct(QRScanInteraction.scan_event_id)))
            .join(
                QRScanEvent,
                QRScanEvent.id == QRScanInteraction.scan_event_id,
            )
            .filter(QRScanEvent.organization_id == organization_id)
        )
        if date_from:
            scans_with_interactions = scans_with_interactions.filter(
                QRScanEvent.scan_timestamp >= date_from
            )
        if date_to:
            scans_with_interactions = scans_with_interactions.filter(
                QRScanEvent.scan_timestamp <= date_to
            )
        scans_with_interactions = scans_with_interactions.scalar() or 0

        total_interactions = (
            self.db.query(func.count(QRScanInteraction.id))
            .join(
                QRScanEvent,
                QRScanEvent.id == QRScanInteraction.scan_event_id,
            )
            .filter(QRScanEvent.organization_id == organization_id)
        )
        if date_from:
            total_interactions = total_interactions.filter(
                QRScanEvent.scan_timestamp >= date_from
            )
        if date_to:
            total_interactions = total_interactions.filter(
                QRScanEvent.scan_timestamp <= date_to
            )
        total_interactions = total_interactions.scalar() or 0

        # Top interaction types
        top_types = (
            self.db.query(
                QRScanInteraction.interaction_type,
                func.count().label("count"),
            )
            .join(
                QRScanEvent,
                QRScanEvent.id == QRScanInteraction.scan_event_id,
            )
            .filter(QRScanEvent.organization_id == organization_id)
        )
        if date_from:
            top_types = top_types.filter(QRScanEvent.scan_timestamp >= date_from)
        if date_to:
            top_types = top_types.filter(QRScanEvent.scan_timestamp <= date_to)
        top_types = (
            top_types.group_by(QRScanInteraction.interaction_type)
            .order_by(func.count().desc())
            .limit(10)
            .all()
        )

        conversion_rate = (
            round(scans_with_interactions / total_scans, 4) if total_scans > 0 else 0.0
        )

        return {
            "total_scans": total_scans,
            "scans_with_cta": scans_with_cta,
            "scans_with_interactions": scans_with_interactions,
            "total_interactions": total_interactions,
            "conversion_rate": conversion_rate,
            "top_interaction_types": [
                {"interaction_type": r.interaction_type, "count": r.count}
                for r in top_types
            ],
        }


# ── QR Scan Interactions ──────────────────────────────────────────────────────


class ScanInteractionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> QRScanInteraction:
        interaction = QRScanInteraction(**data)
        self.db.add(interaction)
        self.db.commit()
        self.db.refresh(interaction)
        return interaction

    def list_by_scan(
        self, scan_event_id: UUID, organization_id: UUID
    ) -> list[QRScanInteraction]:
        return (
            self.db.query(QRScanInteraction)
            .filter(
                QRScanInteraction.scan_event_id == scan_event_id,
                QRScanInteraction.organization_id == organization_id,
            )
            .order_by(QRScanInteraction.created_at.asc())
            .all()
        )


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
