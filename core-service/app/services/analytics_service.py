"""Service layer for Analytics module"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.analytics_repository import (
    CTAConfigRepository,
    MetaCampaignRepository,
    QRScanEventRepository,
    ScanInteractionRepository,
)
from app.schemas.analytics import (
    CTAConfigCreate,
    CTAConfigUpdate,
    MetaCampaignCreate,
    QRScanEventIngest,
    ScanInteractionIngest,
)
from app.services.geoip_service import lookup_ip
from app.services.user_agent_service import parse_user_agent

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.scan_repo = QRScanEventRepository(db)
        self.interaction_repo = ScanInteractionRepository(db)
        self.cta_config_repo = CTAConfigRepository(db)
        self.meta_repo = MetaCampaignRepository(db)

    # ── QR Scan Events ────────────────────────────────────────────────────────

    async def ingest_scan(
        self,
        data: QRScanEventIngest,
        organization_id: UUID,
        request_headers: dict | None = None,
    ):
        """Record a QR scan event with auto-enrichment from HTTP headers.

        Server-side enrichment performed:
        1. User-Agent → parsed device/browser/OS (user_agent_parsed JSONB)
        2. IP address → geo lookup fallback (city/country/lat/lng)
        3. Referer & Accept-Language captured from headers
        """
        payload = data.model_dump()
        payload["organization_id"] = organization_id
        payload["scan_timestamp"] = datetime.now(UTC)

        # ── Enrich from HTTP headers ──────────────────────────────────────
        headers = request_headers or {}
        ua_raw = headers.get("user-agent")
        payload["user_agent_raw"] = ua_raw
        payload["user_agent_parsed"] = parse_user_agent(ua_raw)
        payload["referrer_url"] = headers.get("referer")
        payload["language"] = (headers.get("accept-language") or "")[:10]

        # ── Server-side IP geolocation fallback ───────────────────────────
        if not payload.get("city") and not payload.get("country"):
            geo = await lookup_ip(payload.get("ip_address"))
            if geo:
                for key in ("country", "state", "city", "latitude", "longitude"):
                    if geo.get(key) is not None:
                        payload[key] = geo[key]

        event = self.scan_repo.create(payload)
        logger.info(
            "[ANALYTICS] scan ingested org=%s serial=%s cta=%s ua_parsed=%s",
            organization_id,
            data.serial_number,
            data.cta_action,
            bool(payload["user_agent_parsed"]),
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

    # ── QR Scan Interactions ──────────────────────────────────────────────

    def record_interaction(
        self,
        scan_event_id: UUID,
        data: ScanInteractionIngest,
        organization_id: UUID,
    ):
        """Record a post-scan interaction (click, form submit, call, etc.)."""
        payload = data.model_dump()
        payload["organization_id"] = organization_id
        payload["scan_event_id"] = scan_event_id

        interaction = self.interaction_repo.create(payload)
        logger.info(
            "[ANALYTICS] interaction recorded scan=%s type=%s",
            scan_event_id,
            data.interaction_type,
        )
        return interaction

    def list_interactions(self, scan_event_id: UUID, organization_id: UUID):
        return self.interaction_repo.list_by_scan(scan_event_id, organization_id)

    # ── Phase 4: Enhanced Analytics ──────────────────────────────────────

    def get_cta_breakdown(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ):
        return self.scan_repo.get_cta_breakdown(organization_id, date_from, date_to)

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

    def get_device_timeline(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ):
        return self.scan_repo.get_device_timeline(organization_id, date_from, date_to)

    def get_interaction_funnel(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ):
        return self.scan_repo.get_interaction_funnel(
            organization_id, date_from, date_to
        )

    # ── CTA Configuration ────────────────────────────────────────────────

    def create_cta_config(
        self, data: CTAConfigCreate, organization_id: UUID, product_id: UUID
    ):
        payload = data.model_dump()
        payload["organization_id"] = organization_id
        payload["product_id"] = product_id
        return self.cta_config_repo.create(payload)

    def list_cta_configs(self, organization_id: UUID, product_id: UUID):
        return self.cta_config_repo.list_by_product(organization_id, product_id)

    def get_cta_config(self, config_id: UUID, organization_id: UUID):
        return self.cta_config_repo.get_by_id(config_id, organization_id)

    def update_cta_config(
        self, config_id: UUID, data: CTAConfigUpdate, organization_id: UUID
    ):
        config = self.cta_config_repo.get_by_id(config_id, organization_id)
        if not config:
            return None
        return self.cta_config_repo.update(config, data.model_dump(exclude_unset=True))

    def delete_cta_config(self, config_id: UUID, organization_id: UUID) -> bool:
        config = self.cta_config_repo.get_by_id(config_id, organization_id)
        if not config:
            return False
        self.cta_config_repo.delete(config)
        return True

    # ── Meta Campaigns ────────────────────────────────────────────────────

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
