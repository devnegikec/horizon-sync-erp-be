"""Focused coverage for the QSeal Summary analytics contract."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.repositories.qseal_repository import QSealRepository
from app.services.qseal_service import QSealService


def _query():
    query = Mock()
    query.filter.return_value = query
    query.outerjoin.return_value = query
    query.with_entities.return_value = query
    query.group_by.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    return query


def test_summary_returns_valid_invalid_unique_and_repeat_metrics():
    query = _query()
    query.count.side_effect = [12, 9, 3, 0, 0, 0]
    query.scalar.return_value = 4
    db = Mock()
    db.query.return_value = query

    result = QSealRepository(db).get_scan_summary(
        uuid4(),
        date_from=datetime(2026, 9, 1, tzinfo=UTC),
        date_to=datetime(2026, 9, 14, tzinfo=UTC),
        qseal_type="shipper",
    )

    assert result == {
        "total_scans": 12,
        "valid_scans": 9,
        "invalid_scans": 3,
        "unique_serials": 4,
        "repeat_scans": 5,
        "repeat_scan_rate": 55.6,
        "suspicious_scans": 0,
        "suspicious_rate": 0.0,
        "high_risk_scans": 0,
        "unreviewed_suspicious_scans": 0,
    }
    first_filter = " ".join(str(value) for value in query.filter.call_args_list[0].args)
    assert "organization_id" in first_filter


def test_trends_roll_up_valid_and_invalid_events_by_day():
    query = _query()
    query.all.return_value = [
        SimpleNamespace(date="2026-09-12", verification_status="valid", count=4),
        SimpleNamespace(date="2026-09-12", verification_status="not_found", count=1),
        SimpleNamespace(date="2026-09-13", verification_status="valid", count=2),
    ]
    db = Mock()
    db.query.return_value = query

    result = QSealRepository(db).get_scan_trends(uuid4())

    assert result == {
        "items": [
                {"date": "2026-09-12", "total_scans": 5, "valid_scans": 4, "invalid_scans": 1, "suspicious_scans": 0},
                {"date": "2026-09-13", "total_scans": 2, "valid_scans": 2, "invalid_scans": 0, "suspicious_scans": 0},
        ]
    }


def test_product_analytics_returns_product_and_batch_rows():
    query = _query()
    query.all.return_value = [
        SimpleNamespace(
            product_id=uuid4(),
            product_name="Product A",
            batch="BATCH-A",
            total_scans=Decimal("8"),
            valid_scans=Decimal("7"),
            unique_serials=Decimal("5"),
            last_scan=datetime(2026, 9, 14, tzinfo=UTC),
        )
    ]
    db = Mock()
    db.query.return_value = query

    result = QSealRepository(db).get_product_analytics(uuid4(), limit=10)

    item = result["items"][0]
    assert item["product_name"] == "Product A"
    assert item["batch"] == "BATCH-A"
    assert item["total_scans"] == 8
    assert item["valid_scans"] == 7
    assert item["invalid_scans"] == 1
    assert item["unique_serials"] == 5


def test_geography_and_device_analytics_normalize_nullable_values():
    geo_query = _query()
    geo_query.all.return_value = [
        SimpleNamespace(
            country="India",
            state="Maharashtra",
            city="Pune",
            latitude=Decimal("18.520400"),
            longitude=Decimal("73.856700"),
            total_scans=3,
            valid_scans=2,
        )
    ]
    device_query = _query()
    device_query.all.return_value = [
        SimpleNamespace(device_type=None, total_scans=3, valid_scans=2)
    ]
    db = Mock()
    db.query.side_effect = [geo_query, device_query]
    repo = QSealRepository(db)

    geography = repo.get_geography_analytics(uuid4())
    devices = repo.get_device_analytics(uuid4())

    assert geography["items"][0]["latitude"] == 18.5204
    assert geography["items"][0]["invalid_scans"] == 1
    assert devices["items"] == [
        {"device_type": "unknown", "total_scans": 3, "valid_scans": 2, "invalid_scans": 1}
    ]


def test_analytics_rejects_reversed_date_range():
    service = QSealService(Mock())

    with pytest.raises(HTTPException) as error:
        service.get_scan_analytics_summary(
            uuid4(),
            date_from=datetime(2026, 9, 14, tzinfo=UTC),
            date_to=datetime(2026, 9, 1, tzinfo=UTC),
        )

    assert error.value.status_code == 422


@pytest.mark.parametrize("risk_filter", ["suspicious", "high_risk", "unreviewed"])
def test_risk_filter_is_applied_to_qseal_analytics(risk_filter):
    query = _query()

    filtered = QSealRepository._apply_risk_filter(query, risk_filter)

    assert filtered is query
    assert query.filter.call_count == 1


def test_analytics_rejects_unknown_risk_filter():
    service = QSealService(Mock())

    with pytest.raises(HTTPException) as error:
        service.get_scan_analytics_summary(uuid4(), risk_filter="medium")

    assert error.value.status_code == 422
