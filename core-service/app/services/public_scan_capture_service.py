"""Privacy-safe analytics capture for public QR verification."""

import hashlib
import hmac
import logging
from datetime import UTC, datetime
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.product_item import ProductItem
from app.models.qr_block import QRBlock
from app.models.qr_scan_event import QRScanEvent
from app.models.qseal import QSealParameters, QSealTrack
from app.repositories.qr_verification_repository import QRVerificationRepository
from app.schemas.qr_verification import PublicQRVerifyRequest
from app.services.geoip_service import lookup_ip
from app.services.qseal_suspicion_service import QSealSuspicionService
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
        self.suspicion_service = QSealSuspicionService(db)

    def _apply_suspicion(
        self,
        values: dict,
        *,
        serial_number: str,
        organization_id: UUID,
    ) -> dict:
        """Add explainable risk fields without blocking public verification."""
        try:
            values.update(self.suspicion_service.assess(values))
        except StopIteration:
            # Test doubles and partially configured adapters may not expose
            # optional historical lookup data.
            logger.debug(
                "Suspicious scan history unavailable serial=%s",
                serial_number,
            )
            values.update(
                {
                    "is_suspicious": False,
                    "risk_score": 0,
                    "suspicious_reasons": [],
                    "review_status": "not_flagged",
                    "flagged_at": None,
                }
            )
        except Exception:
            logger.exception(
                "Failed to assess public QR scan suspicion serial=%s org=%s",
                serial_number,
                organization_id,
            )
            values.update(
                {
                    "is_suspicious": False,
                    "risk_score": 0,
                    "suspicious_reasons": [],
                    "review_status": "not_flagged",
                    "flagged_at": None,
                }
            )
        return values

    def _resolve_qseal_context(
        self,
        *,
        item_id: UUID,
        serial_number: str,
        organization_id: UUID,
    ) -> dict:
        """Resolve the denormalized context used by QSeal Analytics.

        Public verification resolves only the ProductItem identity because
        authenticity is the primary concern of that endpoint. QSeal Analytics
        needs the related product, block, batch, and QSeal type as well. Keep
        this lookup best-effort and inside a savepoint so an older deployment
        with a partially migrated QSeal schema can still record a generic
        public scan.
        """
        try:
            with self.db.begin_nested():
                item = (
                    self.db.query(ProductItem)
                    .filter(
                        ProductItem.id == item_id,
                        ProductItem.serial_number == serial_number,
                        ProductItem.organization_id == organization_id,
                        ProductItem.deleted_at.is_(None),
                    )
                    .first()
                )
                parameter = (
                    self.db.query(QSealParameters)
                    .filter(
                        QSealParameters.serial_number == serial_number,
                        QSealParameters.organization_id == organization_id,
                    )
                    .order_by(
                        QSealParameters.created_at.desc(),
                        QSealParameters.id.desc(),
                    )
                    .first()
                )

                # The isinstance checks also keep this helper safe with simple
                # test doubles and ensure an unrelated row cannot be treated
                # as QSeal context if a query adapter returns an unexpected
                # object.
                item = item if isinstance(item, ProductItem) else None
                parameter = (
                    parameter if isinstance(parameter, QSealParameters) else None
                )

                product_id = getattr(item, "product_id", None) or getattr(
                    parameter, "product_id", None
                )
                block_id = getattr(item, "block_id", None) or getattr(
                    parameter, "block_id", None
                )

                batch = None
                if block_id:
                    block = (
                        self.db.query(QRBlock)
                        .filter(
                            QRBlock.id == block_id,
                            QRBlock.organization_id == organization_id,
                        )
                        .first()
                    )
                    batch = getattr(block, "batch", None)

                if not batch and parameter:
                    batch = parameter.dispatch_batch

                qseal_parameter_id = getattr(parameter, "id", None)
                qseal_track_id = (
                    getattr(parameter, "parent_id", None)
                    or getattr(parameter, "parent_app_id", None)
                )
                qseal_type = None
                if qseal_track_id:
                    track = (
                        self.db.query(QSealTrack)
                        .filter(
                            QSealTrack.id == qseal_track_id,
                            QSealTrack.organization_id == organization_id,
                        )
                        .first()
                    )
                    qseal_type = getattr(track, "qseal_type", None)

                # Public ProductItem QR codes are the child/unit scan type.
                # A parameter may exist without a ProductItem relationship,
                # so retain that context too. The product fallback supports
                # legacy items whose block_id was not backfilled.
                if (product_id or block_id or qseal_parameter_id) and not qseal_type:
                    qseal_type = "child_unit"

                if not (product_id or block_id or qseal_parameter_id):
                    return {}

                return {
                    "product_id": product_id,
                    "block_id": block_id,
                    "batch": batch[:50] if isinstance(batch, str) else batch,
                    "qseal_track_id": qseal_track_id,
                    "qseal_parameter_id": qseal_parameter_id,
                    "qseal_type": qseal_type,
                }
        except SQLAlchemyError:
            logger.warning(
                "QSeal context unavailable for public QR serial=%s; "
                "recording generic scan analytics",
                serial_number,
                exc_info=True,
            )
            return {}

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

        # Keep retries idempotent: an existing event retains its original
        # timestamp, so scoring does not treat the same browser retry as a
        # new rapid-repeat scan.
        scan_timestamp = (
            (event.scan_timestamp if event is not None else None) or datetime.now(UTC)
        )
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
            "scan_timestamp": scan_timestamp,
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
        values.update(
            self._resolve_qseal_context(
                item_id=item_id,
                serial_number=request_data.serial_number,
                organization_id=organization_id,
            )
        )

        # Suspicion enrichment is deliberately best-effort. A public visitor
        # must still receive the authenticity result if the historical scan
        # lookup is temporarily unavailable.
        self._apply_suspicion(
            values,
            serial_number=request_data.serial_number,
            organization_id=organization_id,
        )

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

        # Browser location is submitted after the initial verification call.
        # Re-score the event now so rapid cross-location scans are included in
        # Suspicious Activity when the visitor grants location consent.
        if event.serial_number and event.qseal_type:
            values = {
                "organization_id": event.organization_id,
                "serial_number": event.serial_number,
                "qseal_type": event.qseal_type,
                "scan_timestamp": event.scan_timestamp or datetime.now(UTC),
                "verification_status": event.verification_status,
                "device_type": event.device_type,
                "is_bot": event.is_bot,
                "ip_address": event.ip_address,
                "ip_hash": event.ip_hash,
                "latitude": event.latitude,
                "longitude": event.longitude,
            }
            self._apply_suspicion(
                values,
                serial_number=event.serial_number,
                organization_id=event.organization_id,
            )
            for field in (
                "is_suspicious",
                "risk_score",
                "suspicious_reasons",
                "review_status",
                "flagged_at",
            ):
                setattr(event, field, values[field])
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
