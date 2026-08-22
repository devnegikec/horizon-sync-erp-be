"""Focused tests for scan-interaction tenant boundaries and persistence."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.models.qr_scan_interaction import QRScanInteraction
from app.repositories.analytics_repository import ScanInteractionRepository
from app.schemas.analytics import QRScanEventIngest
from app.services.analytics_service import AnalyticsService


def _interaction_data():
    return {
        "organization_id": uuid4(),
        "scan_event_id": uuid4(),
        "interaction_type": "click",
        "interaction_target": "https://example.test/product",
        "interaction_data": {"button_label": "View product"},
    }


def test_create_rejects_scan_from_another_tenant():
    db = Mock()
    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    result = ScanInteractionRepository(db).create(_interaction_data())

    assert result is None
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_create_persists_interaction_for_matching_tenant():
    db = Mock()
    query = db.query.return_value
    query.filter.return_value = query
    resolved_scan_id = uuid4()
    query.first.return_value = SimpleNamespace(id=resolved_scan_id)
    data = _interaction_data()

    result = ScanInteractionRepository(db).create(data)

    interaction = db.add.call_args.args[0]
    assert isinstance(interaction, QRScanInteraction)
    assert interaction.organization_id == data["organization_id"]
    assert interaction.scan_event_id == resolved_scan_id
    assert interaction.interaction_type == "click"
    assert result is interaction
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(interaction)


@pytest.mark.asyncio
async def test_ingest_enriches_headers_product_and_geo(monkeypatch):
    organization_id = uuid4()
    product_item_id = uuid4()
    db = Mock()
    query = db.query.return_value
    query.join.return_value = query
    query.filter.return_value = query
    query.first.return_value = SimpleNamespace(
        id=product_item_id,
        qr_type="dynamic",
    )
    service = AnalyticsService(db)
    service.scan_repo.create = Mock(return_value="created-event")
    monkeypatch.setattr(
        "app.services.analytics_service.parse_user_agent",
        Mock(return_value={"device_type": "mobile", "browser": "Chrome"}),
    )
    monkeypatch.setattr(
        "app.services.analytics_service.lookup_ip",
        AsyncMock(
            return_value={
                "city": "Pune",
                "state": "Maharashtra",
                "country": "India",
                "latitude": 18.5204,
                "longitude": 73.8567,
            }
        ),
    )

    result = await service.ingest_scan(
        QRScanEventIngest(
            serial_number="QSEAL-001",
            ip_address="203.0.113.10",
        ),
        organization_id,
        {
            "user-agent": "Example Mobile Browser",
            "referer": "https://example.test/product",
            "accept-language": "en-IN,en;q=0.9",
        },
    )

    payload = service.scan_repo.create.call_args.args[0]
    assert result == "created-event"
    assert payload["organization_id"] == organization_id
    assert payload["product_item_id"] == product_item_id
    assert payload["qr_type"] == "dynamic"
    assert payload["user_agent_raw"] == "Example Mobile Browser"
    assert payload["language"] == "en-IN,en;q"
    assert payload["city"] == "Pune"
