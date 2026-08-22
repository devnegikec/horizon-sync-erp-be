"""Focused tests for QR analytics chart aggregations."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from sqlalchemy import select

from app.models.qr_scan_event import QRScanEvent
from app.repositories.analytics_repository import QRScanEventRepository


def _query_with_rows(rows):
    query = Mock()
    query.filter.return_value = query
    query.with_entities.return_value = query
    query.group_by.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = rows
    db = Mock()
    db.query.return_value = query
    return db, query


def test_geo_heatmap_returns_valid_decimal_coordinates():
    db, query = _query_with_rows(
        [
            SimpleNamespace(
                latitude=Decimal("40.781637"),
                longitude=Decimal("-73.516699"),
                city="Hicksville",
                state="New York",
                country="United States",
                count=3,
            )
        ]
    )

    result = QRScanEventRepository(db).get_geo_heatmap(uuid4())

    assert result["points"][0]["latitude"] == 40.781637
    assert result["points"][0]["longitude"] == -73.516699
    geo_filter = " ".join(str(value) for value in query.filter.call_args.args)
    assert "latitude IS NOT NULL" in geo_filter
    assert "longitude IS NOT NULL" in geo_filter


def test_device_timeline_groups_known_and_unknown_devices():
    db, _ = _query_with_rows(
        [
            SimpleNamespace(date="2026-08-12", device_type="Mobile", count=2),
            SimpleNamespace(date="2026-08-12", device_type="Desktop", count=1),
            SimpleNamespace(date="2026-08-13", device_type="Smart TV", count=1),
            SimpleNamespace(date="2026-08-13", device_type=None, count=1),
        ]
    )

    result = QRScanEventRepository(db).get_device_timeline(uuid4())

    assert result == {
        "timeline": [
            {
                "date": "2026-08-12",
                "mobile": 2,
                "desktop": 1,
                "tablet": 0,
                "unknown": 0,
            },
            {
                "date": "2026-08-13",
                "mobile": 0,
                "desktop": 0,
                "tablet": 0,
                "unknown": 2,
            },
        ]
    }


def test_interaction_funnel_counts_distinct_converted_scans():
    scan_query = Mock()
    scan_query.filter.return_value = scan_query
    scan_query.count.side_effect = [10, 6]
    scan_query.with_entities.return_value = select(QRScanEvent.id)

    interaction_query = Mock()
    interaction_query.filter.return_value = interaction_query
    interaction_query.count.return_value = 7

    distinct_query = Mock()
    distinct_query.scalar.return_value = 4
    top_types_query = Mock()
    top_types_query.group_by.return_value = top_types_query
    top_types_query.order_by.return_value = top_types_query
    top_types_query.limit.return_value = top_types_query
    top_types_query.all.return_value = [
        SimpleNamespace(interaction_type="click", count=5),
        SimpleNamespace(interaction_type="share", count=2),
    ]
    interaction_query.with_entities.side_effect = [distinct_query, top_types_query]

    db = Mock()
    db.query.side_effect = [scan_query, interaction_query]

    result = QRScanEventRepository(db).get_interaction_funnel(uuid4())

    assert result == {
        "total_scans": 10,
        "scans_with_cta": 6,
        "scans_with_interactions": 4,
        "total_interactions": 7,
        "conversion_rate": 40.0,
        "top_interaction_types": [
            {"type": "click", "count": 5},
            {"type": "share", "count": 2},
        ],
    }
