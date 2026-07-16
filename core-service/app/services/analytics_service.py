"""Service layer for Analytics module"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.analytics_repository import (
    MetaCampaignRepository,
    QRScanEventRepository,
)
from app.schemas.analytics import (
    MetaCampaignCreate,
    QRScanEventIngest,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.scan_repo = QRScanEventRepository(db)
        self.meta_repo = MetaCampaignRepository(db)

    # ── QR Scan Events ────────────────────────────────────────────────────────

    def ingest_scan(
        self,
        data: QRScanEventIngest,
        organization_id: UUID,
    ):
        """Record a QR scan event. Called by the public QR landing page."""
        payload = data.model_dump()
        payload["organization_id"] = organization_id
        payload["scan_timestamp"] = datetime.now(UTC)

        event = self.scan_repo.create(payload)
        logger.info(
            "[ANALYTICS] scan ingested org=%s serial=%s city=%s",
            organization_id,
            data.serial_number,
            data.city,
        )
        return event

    def list_scan_events(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 50,
        serial_number: str | None = None,
        product_item_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ):
        items, total = self.scan_repo.list(
            organization_id,
            page,
            page_size,
            serial_number,
            product_item_id,
            date_from,
            date_to,
        )
        total_pages = (total + page_size - 1) // page_size
        return {
            "events": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }

    def get_scan_analytics(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        serial_number: str | None = None,
    ):
        return self.scan_repo.get_scan_analytics(
            organization_id, date_from, date_to, serial_number
        )

    # ── Meta Campaigns ────────────────────────────────────────────────────────

    def record_meta_snapshot(
        self,
        data: MetaCampaignCreate,
        organization_id: UUID,
    ):
        """Store a new analytics snapshot from Meta Ads API."""
        payload = data.model_dump()
        return self.meta_repo.upsert_snapshot(organization_id, payload)

    def list_meta_campaigns(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        campaign_id: str | None = None,
    ):
        items, total = self.meta_repo.list(
            organization_id, page, page_size, campaign_id
        )
        total_pages = (total + page_size - 1) // page_size
        return {
            "campaigns": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }

    def get_meta_campaign(self, mc_id: UUID, organization_id: UUID):
        return self.meta_repo.get_by_id(mc_id, organization_id)

    # ── CTA Breakdown ─────────────────────────────────────────────────────────

    def get_cta_breakdown(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ):
        return self.scan_repo.get_cta_breakdown(organization_id, date_from, date_to)

    # ── Geo Heatmap ───────────────────────────────────────────────────────────

    def get_geo_heatmap(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 500,
    ):
        return self.scan_repo.get_geo_heatmap(
            organization_id, date_from, date_to, limit
        )

    # ── Device Timeline ───────────────────────────────────────────────────────

    def get_device_timeline(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ):
        return self.scan_repo.get_device_timeline(organization_id, date_from, date_to)

    # ── Interaction Funnel ────────────────────────────────────────────────────

    def get_interaction_funnel(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ):
        return self.scan_repo.get_interaction_funnel(
            organization_id, date_from, date_to
        )
