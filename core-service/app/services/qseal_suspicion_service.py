"""Explainable, tenant-scoped suspicious-scan detection for QSeal events."""

from datetime import UTC, datetime, timedelta
from math import asin, cos, radians, sin, sqrt

from app.models.qr_scan_event import QRScanEvent


class QSealSuspicionService:
    """Evaluate a scan without blocking the public QSeal scan response.

    Rules intentionally use only data already captured by the scan endpoint.
    Each reason is stored as a stable code so clients can render their own
    labels while retaining an auditable explanation for the score.
    """

    INVALID_SCAN = ("invalid_qr", 50)
    BOT_SCAN = ("bot_scan", 40)
    RAPID_REPEAT = ("rapid_repeat", 25)
    DEVICE_CHANGE = ("device_change", 20)
    LOCATION_CHANGE = ("location_change", 40)
    HIGH_VOLUME_SOURCE = ("high_volume_source", 30)

    def __init__(self, db):
        self.db = db

    @staticmethod
    def _distance_km(lat1, lon1, lat2, lon2) -> float:
        """Return the approximate great-circle distance between coordinates."""
        earth_radius_km = 6371.0
        lat1, lon1, lat2, lon2 = map(
            radians, (float(lat1), float(lon1), float(lat2), float(lon2))
        )
        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1
        value = (
            sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
        )
        return earth_radius_km * 2 * asin(sqrt(min(1.0, value)))

    def _previous_for_serial(self, payload: dict) -> list[QRScanEvent]:
        serial = payload.get("serial_number")
        if not serial:
            return []
        timestamp = payload.get("scan_timestamp") or datetime.now(UTC)
        return (
            self.db.query(QRScanEvent)
            .filter(
                QRScanEvent.organization_id == payload["organization_id"],
                QRScanEvent.qseal_type.is_not(None),
                QRScanEvent.serial_number == serial,
                QRScanEvent.scan_timestamp < timestamp,
            )
            .order_by(QRScanEvent.scan_timestamp.desc())
            .limit(20)
            .all()
        )

    def _source_count(self, payload: dict) -> int:
        ip_address = payload.get("ip_address")
        if not ip_address:
            return 0
        timestamp = payload.get("scan_timestamp") or datetime.now(UTC)
        return (
            self.db.query(QRScanEvent)
            .filter(
                QRScanEvent.organization_id == payload["organization_id"],
                QRScanEvent.qseal_type.is_not(None),
                QRScanEvent.ip_address == ip_address,
                QRScanEvent.scan_timestamp >= timestamp - timedelta(hours=1),
                QRScanEvent.scan_timestamp < timestamp,
            )
            .count()
        )

    def assess(self, payload: dict) -> dict:
        reasons: list[str] = []
        score = 0
        timestamp = payload.get("scan_timestamp") or datetime.now(UTC)
        previous = self._previous_for_serial(payload)

        def add(reason: tuple[str, int]) -> None:
            nonlocal score
            reasons.append(reason[0])
            score += reason[1]

        if payload.get("verification_status") != "valid":
            add(self.INVALID_SCAN)
        if payload.get("is_bot"):
            add(self.BOT_SCAN)

        latest = previous[0] if previous else None
        if latest and latest.scan_timestamp:
            elapsed = timestamp - latest.scan_timestamp
            if elapsed <= timedelta(minutes=10):
                add(self.RAPID_REPEAT)
            if (
                payload.get("device_type")
                and latest.device_type
                and payload["device_type"].lower() != latest.device_type.lower()
            ):
                add(self.DEVICE_CHANGE)

        current_lat = payload.get("latitude")
        current_lon = payload.get("longitude")
        if current_lat is not None and current_lon is not None:
            for prior in previous:
                if (
                    prior.latitude is None
                    or prior.longitude is None
                    or not prior.scan_timestamp
                ):
                    continue
                # Compare only against the most recent located scan. A distant
                # older scan inside the window is not evidence of impossible
                # travel when the latest scan is nearby.
                if timestamp - prior.scan_timestamp <= timedelta(hours=6) and (
                    self._distance_km(
                        current_lat, current_lon, prior.latitude, prior.longitude
                    )
                    >= 500
                ):
                    add(self.LOCATION_CHANGE)
                break

        # A source producing 25 or more QSeal events in one hour is useful as
        # a review signal, but it is not enough by itself to block a scan.
        # ``_source_count`` excludes the current scan, so add it back to test
        # the threshold against the full hourly total.
        if self._source_count(payload) + 1 >= 25:
            add(self.HIGH_VOLUME_SOURCE)

        score = min(score, 100)
        is_suspicious = score >= 30
        return {
            "is_suspicious": is_suspicious,
            "risk_score": score,
            "suspicious_reasons": reasons,
            "review_status": "new" if is_suspicious else "not_flagged",
            "flagged_at": timestamp if is_suspicious else None,
        }


def risk_level(score: int) -> str:
    """Map the stored score to the client-facing severity label."""
    if score >= 60:
        return "high"
    if score >= 30:
        return "review"
    return "normal"
