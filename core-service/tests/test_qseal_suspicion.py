"""Unit coverage for explainable QSeal suspicious-scan scoring."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.services.qseal_suspicion_service import QSealSuspicionService, risk_level


def _payload(**overrides):
    payload = {
        "organization_id": uuid4(),
        "serial_number": "QSL-TEST-001",
        "scan_timestamp": datetime.now(UTC),
        "verification_status": "valid",
        "device_type": "mobile",
        "ip_address": None,
        "latitude": None,
        "longitude": None,
        "is_bot": False,
    }
    payload.update(overrides)
    return payload


def test_invalid_bot_scan_is_high_risk_and_explainable():
    detector = QSealSuspicionService(Mock())
    detector._previous_for_serial = Mock(return_value=[])
    detector._source_count = Mock(return_value=0)

    result = detector.assess(_payload(verification_status="not_found", is_bot=True))

    assert result["is_suspicious"] is True
    assert result["risk_score"] == 90
    assert result["suspicious_reasons"] == ["invalid_qr", "bot_scan"]
    assert result["review_status"] == "new"
    assert risk_level(result["risk_score"]) == "high"


def test_rapid_repeat_and_location_change_are_added_to_the_same_event():
    timestamp = datetime.now(UTC)
    detector = QSealSuspicionService(Mock())
    detector._previous_for_serial = Mock(
        return_value=[
            SimpleNamespace(
                scan_timestamp=timestamp - timedelta(minutes=2),
                device_type="desktop",
                latitude=19.0760,
                longitude=72.8777,
            )
        ]
    )
    detector._source_count = Mock(return_value=0)

    result = detector.assess(
        _payload(
            scan_timestamp=timestamp,
            latitude=28.6139,
            longitude=77.2090,
        )
    )

    assert result["is_suspicious"] is True
    assert result["risk_score"] == 85
    assert result["suspicious_reasons"] == [
        "rapid_repeat",
        "device_change",
        "location_change",
    ]
