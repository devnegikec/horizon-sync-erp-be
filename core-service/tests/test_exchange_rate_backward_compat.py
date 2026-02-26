"""Backward compatibility tests for legacy /api/v1/currency/exchange-rates endpoints.

Verifies that existing legacy endpoints continue to function after the ExchangeRate
model was enhanced with organization_id and captured_at columns.

Requirements: 4.10
"""

from datetime import date
from decimal import Decimal

import pytest

from app.models.exchange_rate import ExchangeRate


# ── Legacy Create ───────────────────────────────────────────────────────


def test_legacy_create_exchange_rate(client, db_session):
    """POST /api/v1/currency/exchange-rates creates a record with null organization_id."""
    payload = {
        "from_currency": "USD",
        "to_currency": "EUR",
        "rate": "0.85",
        "effective_date": "2025-01-15",
    }
    resp = client.post("/api/v1/currency/exchange-rates", json=payload)

    assert resp.status_code == 201
    data = resp.json()
    assert data["from_currency"] == "USD"
    assert data["to_currency"] == "EUR"
    assert Decimal(str(data["rate"])) == Decimal("0.85")

    # Verify the DB record has null organization_id (legacy behavior)
    record = db_session.query(ExchangeRate).filter(
        ExchangeRate.from_currency == "USD",
        ExchangeRate.to_currency == "EUR",
    ).first()
    assert record is not None
    assert record.organization_id is None


# ── Legacy List ─────────────────────────────────────────────────────────


def test_legacy_list_exchange_rates(client, db_session):
    """GET /api/v1/currency/exchange-rates returns records including those with null org_id."""
    # Insert a record directly with null organization_id
    record = ExchangeRate(
        from_currency="GBP",
        to_currency="JPY",
        rate=Decimal("188.50"),
        effective_date=date(2025, 3, 1),
        organization_id=None,
    )
    db_session.add(record)
    db_session.commit()

    resp = client.get("/api/v1/currency/exchange-rates")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    currencies = [(r["from_currency"], r["to_currency"]) for r in data]
    assert ("GBP", "JPY") in currencies


# ── Legacy Get Rate for Pair ────────────────────────────────────────────


def test_legacy_get_rate_for_pair(client, db_session):
    """GET /api/v1/currency/exchange-rates/{from}/{to} returns correct rate."""
    record = ExchangeRate(
        from_currency="USD",
        to_currency="CAD",
        rate=Decimal("1.36"),
        effective_date=date(2025, 2, 10),
        organization_id=None,
    )
    db_session.add(record)
    db_session.commit()

    resp = client.get(
        "/api/v1/currency/exchange-rates/USD/CAD",
        params={"effective_date": "2025-02-10"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["from_currency"] == "USD"
    assert data["to_currency"] == "CAD"
    assert Decimal(str(data["rate"])) == Decimal("1.36")


# ── Legacy Update ───────────────────────────────────────────────────────


def test_legacy_update_exchange_rate(client, db_session):
    """PUT /api/v1/currency/exchange-rates/{id} updates rate."""
    record = ExchangeRate(
        from_currency="EUR",
        to_currency="GBP",
        rate=Decimal("0.86"),
        effective_date=date(2025, 4, 1),
        organization_id=None,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)

    update_payload = {
        "rate": "0.89",
        "effective_date": "2025-04-15",
    }
    resp = client.put(
        f"/api/v1/currency/exchange-rates/{record.id}",
        json=update_payload,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(str(data["rate"])) == Decimal("0.89")
    assert data["effective_date"] == "2025-04-15"


# ── Legacy Delete ───────────────────────────────────────────────────────


def test_legacy_delete_exchange_rate(client, db_session):
    """DELETE /api/v1/currency/exchange-rates/{id} removes record."""
    record = ExchangeRate(
        from_currency="AUD",
        to_currency="NZD",
        rate=Decimal("1.08"),
        effective_date=date(2025, 5, 1),
        organization_id=None,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)

    resp = client.delete(f"/api/v1/currency/exchange-rates/{record.id}")
    assert resp.status_code == 204

    # Verify record is gone
    deleted = db_session.query(ExchangeRate).filter(
        ExchangeRate.id == record.id
    ).first()
    assert deleted is None


# ── Null org_id records queryable via legacy endpoints ──────────────────


def test_null_org_id_records_queryable_via_legacy_list(client, db_session):
    """Records created with null org_id are returned by legacy list endpoint."""
    for i, (fc, tc) in enumerate([("CHF", "USD"), ("SEK", "NOK")]):
        db_session.add(ExchangeRate(
            from_currency=fc,
            to_currency=tc,
            rate=Decimal("1.10"),
            effective_date=date(2025, 6, i + 1),
            organization_id=None,
        ))
    db_session.commit()

    resp = client.get("/api/v1/currency/exchange-rates")
    assert resp.status_code == 200
    data = resp.json()
    pairs = [(r["from_currency"], r["to_currency"]) for r in data]
    assert ("CHF", "USD") in pairs
    assert ("SEK", "NOK") in pairs


def test_null_org_id_records_queryable_via_legacy_get_pair(client, db_session):
    """Records with null org_id are returned by legacy get-pair endpoint."""
    db_session.add(ExchangeRate(
        from_currency="INR",
        to_currency="USD",
        rate=Decimal("0.012"),
        effective_date=date(2025, 7, 1),
        organization_id=None,
    ))
    db_session.commit()

    resp = client.get(
        "/api/v1/currency/exchange-rates/INR/USD",
        params={"effective_date": "2025-07-01"},
    )
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["rate"])) == Decimal("0.012")


# ── Legacy Base Currency Endpoints ──────────────────────────────────────


def test_legacy_get_base_currency(client):
    """GET /api/v1/currency/base-currency returns default base currency."""
    resp = client.get("/api/v1/currency/base-currency")

    assert resp.status_code == 200
    data = resp.json()
    assert "base_currency" in data
    # Default is USD when no config exists
    assert data["base_currency"] == "USD"


def test_legacy_set_and_get_base_currency(client):
    """PUT /api/v1/currency/base-currency sets base currency, GET retrieves it."""
    set_resp = client.put(
        "/api/v1/currency/base-currency",
        json={"base_currency": "EUR"},
    )
    assert set_resp.status_code == 200
    assert set_resp.json()["base_currency"] == "EUR"

    get_resp = client.get("/api/v1/currency/base-currency")
    assert get_resp.status_code == 200
    assert get_resp.json()["base_currency"] == "EUR"


# ── Legacy Convert Endpoint ─────────────────────────────────────────────


def test_legacy_convert_currency(client, db_session):
    """POST /api/v1/currency/convert converts amount using exchange rate."""
    # Set up an exchange rate
    db_session.add(ExchangeRate(
        from_currency="USD",
        to_currency="GBP",
        rate=Decimal("0.79"),
        effective_date=date(2025, 1, 1),
        organization_id=None,
    ))
    db_session.commit()

    resp = client.post(
        "/api/v1/currency/convert",
        json={
            "amount": "100.00",
            "from_currency": "USD",
            "to_currency": "GBP",
            "effective_date": "2025-01-01",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["from_currency"] == "USD"
    assert data["to_currency"] == "GBP"
    assert Decimal(str(data["rate"])) == Decimal("0.79")
    assert Decimal(str(data["converted_amount"])) == Decimal("79.0000")
