"""Backfill suspicious-scan scores for QSeal events created before Phase 1.

Usage:
    DEBUG=true python backfill_qseal_suspicion.py --organization-id <UUID>

The command only evaluates QSeal events that still have the neutral
``not_flagged`` state, so reviewed records are not overwritten.
"""

import argparse
import logging
from uuid import UUID

from app.database import SessionLocal
from app.models.product_item import ProductItem
from app.models.qr_scan_event import QRScanEvent
from app.services.qseal_suspicion_service import QSealSuspicionService


def backfill(organization_id: UUID) -> int:
    db = SessionLocal()
    try:
        events = (
            db.query(QRScanEvent)
            .filter(
                QRScanEvent.organization_id == organization_id,
                QRScanEvent.qseal_type.is_not(None),
                QRScanEvent.review_status == "not_flagged",
                QRScanEvent.risk_score == 0,
            )
            .order_by(QRScanEvent.scan_timestamp.asc(), QRScanEvent.id.asc())
            .all()
        )
        detector = QSealSuspicionService(db)
        changed = 0
        for event in events:
            payload = {
                "organization_id": event.organization_id,
                "serial_number": event.serial_number,
                "scan_timestamp": event.scan_timestamp,
                "verification_status": event.verification_status,
                "device_type": event.device_type,
                "ip_address": event.ip_address,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "is_bot": event.is_bot,
            }
            result = detector.assess(payload)
            for key, value in result.items():
                setattr(event, key, value)
            if result["is_suspicious"] and event.product_item_id:
                item = (
                    db.query(ProductItem)
                    .filter(ProductItem.id == event.product_item_id)
                    .first()
                )
                if item:
                    item.is_suspicious = True
            changed += 1
            if changed % 100 == 0:
                db.commit()
        db.commit()
        return changed
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organization-id", required=True, type=UUID)
    args = parser.parse_args()
    count = backfill(args.organization_id)
    logging.basicConfig(level=logging.INFO)
    logging.info("Backfilled %d QSeal scan events", count)


if __name__ == "__main__":
    main()
