"""Public browser entry point for product QR URLs."""

import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.v1.endpoints.public_qr import _client_ip, _scan_event_id
from app.database import get_db
from app.repositories.qr_verification_repository import QRVerificationRepository
from app.schemas.qr_product import QRType, normalize_qr_type
from app.schemas.qr_verification import (
    PublicQRVerifyRequest,
    QRVerificationChannel,
    QRVerificationStatus,
)
from app.services.geoip_service import lookup_ip
from app.services.public_scan_capture_service import (
    PublicScanCaptureService,
    enrich_scan_location,
)
from app.services.qr_verification_service import QRVerificationService

router = APIRouter(tags=["Public QR Redirect"])
logger = logging.getLogger(__name__)


def _text_value(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _append_query(url: str, values: dict[str, object | None]) -> str:
    parsed = urlsplit(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query.extend(
        (key, text)
        for key, value in values.items()
        if value is not None
        for text in [_text_value(value)]
    )
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
    )


async def _location_values(request: Request) -> tuple[str | None, str | None]:
    location = await lookup_ip(_client_ip(request))
    if not location:
        return None, None
    return location.get("country"), location.get("state")


@router.get(
    "/g/{gtin}/s/{serial_number}/{timestamp}",
    name="redirect_qr_to_client_product",
    summary="Redirect a product QR directly to its client URL",
)
async def redirect_qr_to_client(
    gtin: str,
    serial_number: str,
    timestamp: str,
    request: Request,
    signature: str | None = Query(None, alias="c"),
    qr_channel: QRVerificationChannel | None = Query(None, alias="qr"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """Implement the legacy Django direct-redirect behavior.

    This route deliberately does not authenticate the QR. When the product
    opts into client redirect mode, the browser is sent to the configured
    client URL immediately for every QR type.
    """
    repo = QRVerificationRepository(db)
    identity = repo.resolve_active_item_identity(serial_number)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR code not found",
        )

    item_id, organization_id = identity
    item = repo.get_tenant_item_for_update(
        item_id,
        serial_number,
        organization_id,
    )
    product = item.product if item else None
    redirect_url = QRVerificationService._client_redirect_url(product)
    if (
        item is None
        or product is None
        or product.organization_id != organization_id
        or product.deleted_at is not None
        or not product.is_active
        or not redirect_url
    ):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Direct product redirect is not enabled for this QR",
        )

    resolved_qr_channel = (
        qr_channel if isinstance(qr_channel, QRVerificationChannel) else None
    )
    client_ip = _client_ip(request)
    country, region = await _location_values(request)
    tenant = str(organization_id)
    # Query parsers may decode legacy '+' characters in base64 signatures as
    # spaces. Restore them before passing the signed value to the client.
    signed_value = (signature or "").replace(" ", "+")
    common = {
        "country": country,
        "region": region,
        "tenant": tenant,
    }

    if product.activation_method == "pre":
        params = {
            "serial": serial_number,
            "timestamp": timestamp,
            "signature": signed_value,
            **common,
        }
    else:
        activation = repo.get_activation_details(
            product.id,
            serial_number,
            organization_id,
        )
        if item.qr_deactive or item.qr_deactive_unit or activation is None:
            params = {"status": "deactive", **common}
        else:
            currency = _text_value(activation.currency)
            mrp = _text_value(activation.mrp)
            if mrp and currency:
                mrp = f"{mrp}({currency})"
            params = {
                "serial": serial_number,
                "timestamp": timestamp,
                "signature": signed_value,
                "m_date": activation.manufacturing_date,
                "m_unit": activation.manufacturing_unit,
                "expiry": activation.expiry_date,
                "destination": activation.destination_market,
                "mrp": mrp,
                "batch": activation.dispatch_batch,
                "gtin": getattr(item.sku, "gtin", None) or product.gtin or gtin,
                **common,
            }

    # Direct browser redirects do not pass through POST /public/qr/verify, so
    # capture the scan here before returning the HTTP redirect. This mirrors
    # the normal public verification flow and keeps redirect-mode scans in
    # QSeal analytics.
    try:
        scan_data = PublicQRVerifyRequest(
            gtin=gtin,
            serial_number=serial_number,
            timestamp=timestamp,
            signature=signed_value or "direct-redirect",
            qr_channel=resolved_qr_channel,
        )
        qr_type = (
            normalize_qr_type(
                getattr(getattr(item, "block", None), "qr_type", None)
                or getattr(product, "qr_type", None)
            )
            or QRType.DYNAMIC
        )
        captured_id = PublicScanCaptureService(db).capture(
            event_id=_scan_event_id(request),
            request_data=scan_data,
            verification_result={
                # This route never authenticates the QR, so the scan is
                # recorded as a redirect rather than a successful verification.
                "verification_status": QRVerificationStatus.REDIRECT,
                "authentic": False,
                "qr_type": qr_type.value,
                "challenge_type": None,
            },
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent"),
            referrer=request.headers.get("referer"),
            language=request.headers.get("accept-language"),
        )
        if captured_id and background_tasks is not None:
            background_tasks.add_task(
                enrich_scan_location,
                captured_id,
                client_ip,
            )
    except Exception:
        db.rollback()
        # Analytics must never prevent the configured client redirect.
        logger.exception(
            "Public QR redirect analytics capture failed serial=%s",
            serial_number,
        )

    db.rollback()
    return RedirectResponse(
        url=_append_query(redirect_url, params),
        status_code=status.HTTP_302_FOUND,
    )
