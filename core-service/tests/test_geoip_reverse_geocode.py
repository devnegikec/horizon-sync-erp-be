"""Tests for the opt-in reverse-geocoding path."""

import asyncio

from app.services import geoip_service


def test_reverse_geocode_is_disabled_without_a_configured_provider(monkeypatch):
    """No provider configured means visitor GPS never leaves the platform."""
    monkeypatch.setattr(geoip_service.settings, "reverse_geocoding_url", "")

    assert asyncio.run(geoip_service.reverse_geocode(12.9716, 77.5946)) is None


def test_user_agent_identifies_the_operator_when_configured(monkeypatch):
    monkeypatch.setattr(
        geoip_service.settings, "reverse_geocoding_contact", "ops@example.com"
    )

    agent = geoip_service._reverse_geocoding_user_agent()

    assert agent.startswith("Brandwise-QSeal/")
    assert agent.endswith("(+ops@example.com)")


def test_user_agent_omits_empty_contact(monkeypatch):
    monkeypatch.setattr(geoip_service.settings, "reverse_geocoding_contact", "")

    assert "(" not in geoip_service._reverse_geocoding_user_agent()
