"""Tests for the browser-level client product redirect route."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest

from app.api.qr_redirect import redirect_qr_to_client, router
from app.schemas.qr_verification import QRVerificationChannel


def _item(*, activation_method="pre", active=True):
    organization_id = uuid4()
    product = SimpleNamespace(
        id=uuid4(),
        organization_id=organization_id,
        deleted_at=None,
        is_active=True,
        redirect_to_client=True,
        client_product_auth_url="https://client.example.com/auth?source=qseal",
        activation_method=activation_method,
        gtin="0123456789012",
    )
    item = SimpleNamespace(
        id=uuid4(),
        organization_id=organization_id,
        serial_number="PRO-ABC12345",
        product=product,
        sku=SimpleNamespace(gtin="0123456789012"),
        qr_deactive=not active,
        qr_deactive_unit=not active,
    )
    return item


def _repo(item):
    repo = Mock()
    repo.resolve_active_item_identity.return_value = (
        item.id,
        item.organization_id,
    )
    repo.get_tenant_item_for_update.return_value = item
    return repo


def _stub_analytics(monkeypatch):
    service = Mock()
    service.capture.return_value = None
    monkeypatch.setattr(
        "app.api.qr_redirect.PublicScanCaptureService",
        lambda _db: service,
    )
    monkeypatch.setattr("app.api.qr_redirect._client_ip", lambda _request: None)
    monkeypatch.setattr("app.api.qr_redirect._scan_event_id", lambda _request: uuid4())
    return service


def test_browser_qr_redirect_route_is_registered():
    assert any(
        route.path == "/g/{gtin}/s/{serial_number}/{timestamp}"
        for route in router.routes
    )


@pytest.mark.asyncio
async def test_pre_activation_redirect_appends_legacy_client_parameters(monkeypatch):
    item = _item()
    repo = _repo(item)
    db = Mock()
    _stub_analytics(monkeypatch)
    monkeypatch.setattr("app.api.qr_redirect.QRVerificationRepository", lambda _db: repo)

    async def location(_request):
        return "India", "Maharashtra"

    monkeypatch.setattr("app.api.qr_redirect._location_values", location)

    response = await redirect_qr_to_client(
        "0123456789012",
        item.serial_number,
        "1770000000000",
        Mock(),
        signature="MEQC ABC/DEF=",
        db=db,
    )

    query = parse_qs(urlsplit(response.headers["location"]).query)
    assert response.status_code == 302
    assert urlsplit(response.headers["location"]).path == "/auth"
    assert query["serial"] == [item.serial_number]
    assert query["timestamp"] == ["1770000000000"]
    assert query["signature"] == ["MEQC+ABC/DEF="]
    assert query["country"] == ["India"]
    assert query["region"] == ["Maharashtra"]
    assert query["tenant"] == [str(item.organization_id)]
    db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_active_post_activation_redirect_appends_activation_metadata(monkeypatch):
    item = _item(activation_method="post")
    item.qr_deactive = False
    item.qr_deactive_unit = False
    repo = _repo(item)
    repo.get_activation_details.return_value = SimpleNamespace(
        manufacturing_date=date(2026, 10, 1),
        manufacturing_unit="Plant A",
        expiry_date=date(2028, 10, 1),
        destination_market="US",
        mrp="499.00",
        currency="USD",
        dispatch_batch="BATCH-01",
    )
    db = Mock()
    _stub_analytics(monkeypatch)
    monkeypatch.setattr("app.api.qr_redirect.QRVerificationRepository", lambda _db: repo)
    monkeypatch.setattr(
        "app.api.qr_redirect._location_values",
        lambda _request: _location(),
    )

    response = await redirect_qr_to_client(
        "0123456789012",
        item.serial_number,
        "1770000000000",
        Mock(),
        signature="signed-value",
        db=db,
    )

    query = parse_qs(urlsplit(response.headers["location"]).query)
    assert query["m_date"] == ["2026-10-01"]
    assert query["m_unit"] == ["Plant A"]
    assert query["expiry"] == ["2028-10-01"]
    assert query["destination"] == ["US"]
    assert query["mrp"] == ["499.00(USD)"]
    assert query["batch"] == ["BATCH-01"]
    assert query["gtin"] == ["0123456789012"]


@pytest.mark.asyncio
async def test_direct_redirect_captures_analytics_before_redirect(monkeypatch):
    item = _item()
    repo = _repo(item)
    db = Mock()
    capture_service = _stub_analytics(monkeypatch)
    event_id = uuid4()
    capture_service.capture.return_value = event_id
    monkeypatch.setattr(
        "app.api.qr_redirect._scan_event_id",
        lambda _request: event_id,
    )
    monkeypatch.setattr("app.api.qr_redirect.QRVerificationRepository", lambda _db: repo)

    async def location(_request):
        return None, None

    monkeypatch.setattr("app.api.qr_redirect._location_values", location)
    request = SimpleNamespace(
        client=None,
        headers={
            "user-agent": "Mozilla/5.0",
            "referer": "https://scanner.example/",
            "accept-language": "en-US",
        },
    )
    background_tasks = Mock()

    response = await redirect_qr_to_client(
        "0123456789012",
        item.serial_number,
        "1770000000000",
        request,
        signature="signed-value",
        qr_channel=QRVerificationChannel.OVERT,
        background_tasks=background_tasks,
        db=db,
    )

    assert response.status_code == 302
    capture_kwargs = capture_service.capture.call_args.kwargs
    assert capture_kwargs["event_id"] == event_id
    assert capture_kwargs["request_data"].serial_number == item.serial_number
    assert capture_kwargs["request_data"].qr_channel == QRVerificationChannel.OVERT
    assert capture_kwargs["verification_result"]["authentic"] is True
    background_tasks.add_task.assert_called_once()


async def _location():
    return "India", "Maharashtra"
