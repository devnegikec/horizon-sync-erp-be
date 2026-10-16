"""Backfill suspicious-scan scores for QSeal events created before Phase 1.

Usage:
    DEBUG=true python backfill_qseal_suspicion.py --organization-id <UUID>

The command only evaluates QSeal events that still have the neutral
``not_flagged`` state, so reviewed records are not overwritten.
"""

import argparse
import logging
from uuid import UUID

import sqlalchemy as sa

from app.database import SessionLocal
from app.models.product_item import ProductItem
from app.models.qr_scan_event import QRScanEvent
from app.services.qseal_suspicion_service import QSealSuspicionService

BATCH_SIZE = 500


def _payload_for(event: QRScanEvent) -> dict:
    return {
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


def backfill(organization_id: UUID) -> int:
    """Re-score eligible events in bounded batches.

    Events are streamed with a keyset cursor instead of loading the whole
    tenant into memory, and each batch commits before the next one starts.
    """
    db = SessionLocal()
    detector = QSealSuspicionService(db)
    changed = 0
    last_key: tuple | None = None
    try:
        while True:
            query = db.query(QRScanEvent).filter(
                QRScanEvent.organization_id == organization_id,
                QRScanEvent.qseal_type.is_not(None),
                QRScanEvent.review_status == "not_flagged",
                QRScanEvent.risk_score == 0,
                QRScanEvent.scan_timestamp.is_not(None),
            )
            if last_key is not None:
                last_timestamp, last_id = last_key
                query = query.filter(
                    sa.or_(
                        QRScanEvent.scan_timestamp > last_timestamp,
                        sa.and_(
                            QRScanEvent.scan_timestamp == last_timestamp,
                            QRScanEvent.id > last_id,
                        ),
                    )
                )
            events = (
                query.order_by(QRScanEvent.scan_timestamp.asc(), QRScanEvent.id.asc())
                .limit(BATCH_SIZE)
                .all()
            )
            if not events:
                break

            suspicious_item_ids: set[UUID] = set()
            for event in events:
                result = detector.assess(_payload_for(event))
                for key, value in result.items():
                    setattr(event, key, value)
                if result["is_suspicious"] and event.product_item_id:
                    suspicious_item_ids.add(event.product_item_id)

            if suspicious_item_ids:
                # Flag every affected item in one statement rather than one
                # query per suspicious event.
                db.query(ProductItem).filter(
                    ProductItem.id.in_(suspicious_item_ids)
                ).update(
                    {ProductItem.is_suspicious: True},
                    synchronize_session=False,
                )

            last_event = events[-1]
            last_key = (last_event.scan_timestamp, last_event.id)
            db.commit()
            changed += len(events)
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
