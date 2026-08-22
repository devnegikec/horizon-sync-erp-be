"""Tests for idempotent, privacy-safe public scan analytics capture."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.api.v1.endpoints.public_qr import _client_ip
from app.models.qr_scan_event import QRScanEvent
from app.repositories.qr_verification_repository import QRVerificationRepository
from app.schemas.qr_verification import PublicQRVerifyRequest
from app.services.geoip_service import reverse_geocode
from app.services.public_scan_capture_service import (
    PublicScanCaptureService,
    _privacy_safe_referrer,
)


def _request() -> PublicQRVerifyRequest:
    return PublicQRVerifyRequest(
        gtin="0123456789012",
        serial_number="PRO-ABC12345",
        timestamp="1770000000000",
        signature="signed-value",
    )


def test_capture_creates_privacy_safe_event(monkeypatch):
    db = Mock()
    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None
    item_id = uuid4()
    organization_id = uuid4()
    monkeypatch.setattr(
        QRVerificationRepository,
        "resolve_active_item_identity",
        lambda *_: (item_id, organization_id),
    )

    event_id = uuid4()
    captured = PublicScanCaptureService(db).capture(
        event_id=event_id,
        request_data=_request(),
        verification_result={
            "verification_status": "authentic",
            "authentic": True,
            "qr_type": "dynamic",
            "challenge_type": None,
        },
        client_ip="203.0.113.10",
        user_agent="Mozilla/5.0 (Linux; Android 13) Mobile",
        referrer="https://example.com/product?token=secret#private",
        language="en-IN,en;q=0.9",
    )

    event = db.add.call_args.args[0]
    assert isinstance(event, QRScanEvent)
    assert captured == event_id
    assert event.organization_id == organization_id
    assert event.product_item_id == item_id
    assert event.ip_address is None
    assert len(event.ip_hash) == 64
    assert event.referrer_url == "https://example.com/product"
    assert event.verification_status == "authentic"
    db.commit.assert_called_once()


def test_capture_updates_existing_event_instead_of_counting_retry(monkeypatch):
    organization_id = uuid4()
    event_id = uuid4()
    existing = QRScanEvent(
        event_id=event_id,
        organization_id=organization_id,
        verification_status="verification_required",
    )
    db = Mock()
    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = existing
    monkeypatch.setattr(
        QRVerificationRepository,
        "resolve_active_item_identity",
        lambda *_: (uuid4(), organization_id),
    )

    PublicScanCaptureService(db).capture(
        event_id=event_id,
        request_data=_request(),
        verification_result={"verification_status": "authentic", "authentic": True},
        client_ip=None,
        user_agent=None,
        referrer=None,
        language=None,
    )

    assert existing.verification_status == "authentic"
    assert existing.authentic is True
    db.add.assert_not_called()
    db.commit.assert_called_once()


def test_browser_location_persists_formatted_street_address():
    event = QRScanEvent(event_id=uuid4(), organization_id=uuid4())
    db = Mock()
    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = event

    updated = PublicScanCaptureService(db).update_browser_location(
        event.event_id,
        40.781637,
        -73.516699,
        25,
        {
            "city": "Hicksville",
            "state": "New York",
            "country": "United States",
            "street_address": (
                "12 Private Road, Hicksville, New York, United States"
            ),
        },
    )

    assert updated is True
    assert event.street_address == (
        "12 Private Road, Hicksville, New York, United States"
    )
    assert event.location_source == "browser"
    db.commit.assert_called_once()


def test_referrer_discards_query_fragment_and_unsafe_schemes():
    assert (
        _privacy_safe_referrer("https://example.com/path?access_token=x#secret")
        == "https://example.com/path"
    )
    assert _privacy_safe_referrer("javascript:alert(1)") is None


def test_forwarded_ip_is_only_trusted_from_private_proxy():
    proxied = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        headers={"x-forwarded-for": "203.0.113.20, 10.0.0.2"},
    )
    direct = SimpleNamespace(
        client=SimpleNamespace(host="198.51.100.8"),
        headers={"x-forwarded-for": "203.0.113.20"},
    )

    assert _client_ip(proxied) == "203.0.113.20"
    assert _client_ip(direct) == "198.51.100.8"


@pytest.mark.asyncio
async def test_reverse_geocode_returns_formatted_street_address(monkeypatch):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "display_name": "12 Private Road, Hicksville, New York, United States",
        "address": {
            "road": "Private Road",
            "town": "Hicksville",
            "state": "New York",
            "country": "United States",
        },
    }
    client = AsyncMock()
    client.get.return_value = response
    context = AsyncMock()
    context.__aenter__.return_value = client
    monkeypatch.setattr(
        "app.services.geoip_service.httpx.AsyncClient",
        Mock(return_value=context),
    )
    monkeypatch.setattr(
        "app.services.geoip_service.settings.reverse_geocoding_url",
        "https://geocoder.example.test/reverse",
    )

    result = await reverse_geocode(40.781637, -73.516699)

    assert result == {
        "city": "Hicksville",
        "state": "New York",
        "country": "United States",
        "street_address": "12 Private Road, Hicksville, New York, United States",
    }
    assert client.get.call_args.kwargs["params"]["zoom"] == 18
