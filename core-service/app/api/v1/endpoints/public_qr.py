"""Public QR verification endpoints. No user authentication is required."""

import ipaddress
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.qr_verification import (
    PublicQRVerifyRequest,
    PublicQRVerifyResponse,
    PublicScanLocationUpdate,
)
from app.services.geoip_service import reverse_geocode
from app.services.public_scan_capture_service import (
    PublicScanCaptureService,
    enrich_scan_location,
)
from app.services.qr_verification_service import QRVerificationService

router = APIRouter()
logger = logging.getLogger(__name__)

_TRUSTED_PROXY_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("::1/128"),
)


def _scan_event_id(request: Request) -> UUID:
    value = request.headers.get("x-scan-event-id")
    if value:
        try:
            return UUID(value)
        except ValueError:
            pass
    return uuid4()


def _client_ip(request: Request) -> str | None:
    """Use forwarding headers only when the direct peer is a private proxy."""
    peer = request.client.host if request.client else None
    if not peer:
        return None
    try:
        peer_ip = ipaddress.ip_address(peer)
    except ValueError:
        return None

    candidate = peer
    if any(peer_ip in network for network in _TRUSTED_PROXY_NETWORKS):
        candidate = (
            request.headers.get("cf-connecting-ip")
            or request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
            or peer
        )
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return str(peer_ip)


@router.post(
    "/verify",
    response_model=PublicQRVerifyResponse,
    summary="Verify a public QSeal QR code",
    description=(
        "Resolves the globally unique serial, verifies its ECDSA signature, "
        "and applies the configured QR-type and activation rules."
    ),
)
async def verify_public_qr(
    data: PublicQRVerifyRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    result = QRVerificationService(db).verify(data)
    event_id = _scan_event_id(request)
    client_ip = _client_ip(request)
    try:
        captured_id = PublicScanCaptureService(db).capture(
            event_id=event_id,
            request_data=data,
            verification_result=result,
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent"),
            referrer=request.headers.get("referer"),
            language=request.headers.get("accept-language"),
        )
        if captured_id:
            result["scan_event_id"] = captured_id
            background_tasks.add_task(
                enrich_scan_location,
                captured_id,
                client_ip,
            )
    except Exception:
        db.rollback()
        # Analytics must never interrupt a consumer's authenticity result.
        logger.exception("Public QR analytics capture failed")
    return PublicQRVerifyResponse(**result)


@router.patch(
    "/scans/{event_id}/location",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Add optional browser location to a public scan",
)
async def update_public_scan_location(
    event_id: UUID,
    data: PublicScanLocationUpdate,
    db: Session = Depends(get_db),
) -> None:
    location_names = await reverse_geocode(data.latitude, data.longitude)
    updated = PublicScanCaptureService(db).update_browser_location(
        event_id,
        data.latitude,
        data.longitude,
        data.accuracy_meters,
        location_names,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Scan event not found")
