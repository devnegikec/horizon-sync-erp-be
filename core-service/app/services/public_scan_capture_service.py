"""Privacy-safe analytics capture for public QR verification."""

import hashlib
import hmac
import logging
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.qr_scan_event import QRScanEvent
from app.repositories.qr_verification_repository import QRVerificationRepository
from app.schemas.qr_verification import PublicQRVerifyRequest
from app.services.geoip_service import lookup_ip
from app.services.user_agent_service import parse_user_agent

logger = logging.getLogger(__name__)


def _privacy_safe_referrer(value: str | None) -> str | None:
    """Keep origin/path while discarding query parameters and fragments."""
    if not value:
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"}:
            return None
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))[:2000]
    except ValueError:
        return None


def _hash_ip(ip_address: str | None) -> str | None:
    if not ip_address:
        return None
    return hmac.new(
        settings.secret_key.encode(),
        ip_address.encode(),
        hashlib.sha256,
    ).hexdigest()


class PublicScanCaptureService:
    """Create or update one scan event for a browser-generated event UUID."""

    def __init__(self, db: Session):
        self.db = db

    def capture(
        self,
        *,
        event_id: UUID,
        request_data: PublicQRVerifyRequest,
        verification_result: dict,
        client_ip: str | None,
        user_agent: str | None,
        referrer: str | None,
        language: str | None,
    ) -> UUID | None:
        identity = QRVerificationRepository(
            self.db
        ).resolve_active_item_identity(request_data.serial_number)
        if identity is None:
            # Without a resolved item there is no trustworthy tenant owner.
            return None

        item_id, organization_id = identity
        parsed_agent = parse_user_agent(user_agent)
        event = (
            self.db.query(QRScanEvent)
            .filter(QRScanEvent.event_id == event_id)
            .first()
        )
        if event is not None and event.organization_id != organization_id:
            logger.warning("Rejected cross-tenant scan event reuse: %s", event_id)
            return None

        status = verification_result.get("verification_status") or "invalid"
        if hasattr(status, "value"):
            status = status.value
        qr_type = verification_result.get("qr_type")
        if hasattr(qr_type, "value"):
            qr_type = qr_type.value
        values = {
            "organization_id": organization_id,
            "product_item_id": item_id,
            "serial_number": request_data.serial_number,
            "verification_status": str(status),
            "authentic": bool(verification_result.get("authentic", False)),
            "qr_type": qr_type,
            "qr_channel": (
                request_data.qr_channel.value if request_data.qr_channel else None
            ),
            "user_agent_raw": user_agent[:2000] if user_agent else None,
            "user_agent_parsed": parsed_agent,
            "device_type": (
                parsed_agent.get("device_type") if parsed_agent else None
            ),
            "os": parsed_agent.get("os") if parsed_agent else None,
            "browser": parsed_agent.get("browser") if parsed_agent else None,
            "is_bot": bool(parsed_agent and parsed_agent.get("is_bot")),
            "ip_hash": _hash_ip(client_ip),
            "referrer_url": _privacy_safe_referrer(referrer),
            "language": language[:10] if language else None,
            "extra_data": {
                "gtin": request_data.gtin,
                "challenge_type": verification_result.get("challenge_type"),
            },
        }

        if event is None:
            event = QRScanEvent(event_id=event_id, **values)
            self.db.add(event)
        else:
            for field, value in values.items():
                setattr(event, field, value)

        try:
            self.db.commit()
        except IntegrityError:
            # A concurrent retry may win the unique event_id insert race.
            self.db.rollback()
            event = (
                self.db.query(QRScanEvent)
                .filter(QRScanEvent.event_id == event_id)
                .first()
            )
            if event is None or event.organization_id != organization_id:
                raise
        return event_id

    def update_browser_location(
        self,
        event_id: UUID,
        latitude: float,
        longitude: float,
        accuracy_meters: int | None,
        location_names: dict | None = None,
    ) -> bool:
        event = (
            self.db.query(QRScanEvent)
            .filter(QRScanEvent.event_id == event_id)
            .first()
        )
        if event is None:
            return False
        event.latitude = latitude
        event.longitude = longitude
        event.location_source = "browser"
        event.location_accuracy_meters = accuracy_meters
        if location_names:
            event.city = location_names.get("city")
            event.state = location_names.get("state")
            event.country = location_names.get("country")
            event.street_address = location_names.get("street_address")
        self.db.commit()
        return True


async def enrich_scan_location(event_id: UUID, client_ip: str | None) -> None:
    """Best-effort IP enrichment executed after the verification response."""
    geo = await lookup_ip(client_ip)
    if not geo:
        return
    db = SessionLocal()
    try:
        event = (
            db.query(QRScanEvent)
            .filter(QRScanEvent.event_id == event_id)
            .first()
        )
        if event is None or event.location_source == "browser":
            return
        for field in ("country", "state", "city", "latitude", "longitude"):
            setattr(event, field, geo.get(field))
        event.location_source = "ip"
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to enrich public scan location: %s", event_id)
    finally:
        db.close()
