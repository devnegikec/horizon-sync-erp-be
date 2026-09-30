"""Seed safe, repeatable QSeal scan data for local analytics testing.

The script only creates QRScanEvent rows. It does not create products, blocks,
or product items, and it never deletes existing data. Each generated event has
an idempotent event_id and is tagged in extra_data.

Usage:
    DEBUG=true python seed_qseal_analytics_demo.py --organization-id <ORG_UUID>
    DEBUG=true python seed_qseal_analytics_demo.py --organization-id <ORG_UUID> --days 90
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models.product_item import (
    ProductItem,  # noqa: F401 - registers relationship mapper
)
from app.models.product_sku import (
    ProductSKU,  # noqa: F401 - registers relationship mapper
)
from app.models.qr_block import QRBlock
from app.models.qr_product import QRProduct
from app.models.qr_scan_event import QRScanEvent

SEED_NAME = "qseal-analytics-demo"
# Fixed key serializing concurrent seed runs; must fit a signed 64-bit int.
SEED_LOCK_KEY = 90210120240914
LOCATIONS = [
    {
        "city": "New York",
        "state": "New York",
        "country": "United States",
        "latitude": 40.7128,
        "longitude": -74.0060,
    },
    {
        "city": "London",
        "state": "England",
        "country": "United Kingdom",
        "latitude": 51.5074,
        "longitude": -0.1278,
    },
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
        "latitude": 19.0760,
        "longitude": 72.8777,
    },
    {
        "city": "Toronto",
        "state": "Ontario",
        "country": "Canada",
        "latitude": 43.6532,
        "longitude": -79.3832,
    },
    {"city": None, "state": None, "country": None, "latitude": None, "longitude": None},
]
DEVICES = [
    {"device_type": "mobile", "os": "iOS", "browser": "Safari"},
    {"device_type": "mobile", "os": "Android", "browser": "Chrome"},
    {"device_type": "desktop", "os": "Windows", "browser": "Chrome"},
    {"device_type": "tablet", "os": "iPadOS", "browser": "Safari"},
]
QSEAL_TYPES = ["unit", "case", "pallet"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed QSeal analytics demo scan events"
    )
    parser.add_argument(
        "--organization-id", required=True, help="Tenant organization UUID to seed"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        choices=[30, 60, 90],
        help="Number of days of history to create",
    )
    parser.add_argument(
        "--events-per-day",
        type=int,
        default=3,
        choices=[1, 2, 3, 4, 5],
        help="Events per product per day",
    )
    return parser.parse_args()


def make_event_id(
    organization_id: uuid.UUID, product_id: uuid.UUID, day: int, index: int
) -> uuid.UUID:
    return uuid.uuid5(
        uuid.NAMESPACE_URL, f"{SEED_NAME}:{organization_id}:{product_id}:{day}:{index}"
    )


def seed(organization_id: uuid.UUID, days: int, events_per_day: int) -> tuple[int, int]:
    db = SessionLocal()
    try:
        # Serialize concurrent runs so the read-then-insert check below cannot
        # race and trip the unique ``event_id`` constraint. The advisory lock
        # is released automatically when the transaction ends.
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SEED_LOCK_KEY})

        products = (
            db.query(QRProduct)
            .filter(
                QRProduct.organization_id == organization_id,
                QRProduct.deleted_at.is_(None),
            )
            .order_by(QRProduct.created_at)
            .limit(10)
            .all()
        )
        if not products:
            raise RuntimeError(
                f"No QR products found for organization {organization_id}. Create a QSeal product first."
            )

        product_ids = [product.id for product in products]
        existing_ids = {
            row[0]
            for row in db.query(QRScanEvent.event_id)
            .filter(
                QRScanEvent.organization_id == organization_id,
                QRScanEvent.event_id.is_not(None),
            )
            .all()
        }
        now = datetime.now(UTC)
        events: list[QRScanEvent] = []

        for product_index, product in enumerate(products):
            block = (
                db.query(QRBlock)
                .filter(
                    QRBlock.organization_id == organization_id,
                    QRBlock.product_id == product.id,
                    QRBlock.deleted_at.is_(None),
                )
                .order_by(QRBlock.created_at)
                .first()
            )
            batch = (
                block.batch
                if block and block.batch
                else f"DEMO-{product_index + 1:02d}"
            )
            serials = [
                f"DEMO-{product_index + 1:02d}-{number:04d}" for number in range(1, 7)
            ]

            for day in range(days):
                for event_index in range(events_per_day):
                    event_id = make_event_id(
                        organization_id, product.id, day, event_index
                    )
                    if event_id in existing_ids:
                        continue

                    location = LOCATIONS[
                        (day + event_index + product_index) % len(LOCATIONS)
                    ]
                    device = DEVICES[(day + event_index) % len(DEVICES)]
                    is_invalid = (day + event_index + product_index) % 11 == 0
                    scan_time = now - timedelta(
                        days=day, hours=(event_index * 3 + product_index) % 12
                    )
                    serial = serials[(day + event_index) % len(serials)]

                    events.append(
                        QRScanEvent(
                            id=uuid.uuid4(),
                            event_id=event_id,
                            organization_id=organization_id,
                            product_id=product.id,
                            block_id=block.id if block else None,
                            serial_number=serial,
                            batch=batch,
                            qseal_type=QSEAL_TYPES[
                                (day + product_index) % len(QSEAL_TYPES)
                            ],
                            qr_type=product.qr_type or "dynamic",
                            scan_timestamp=scan_time,
                            verification_status="invalid" if is_invalid else "valid",
                            authentic=not is_invalid,
                            device_type=device["device_type"],
                            os=device["os"],
                            browser=device["browser"],
                            city=location["city"],
                            state=location["state"],
                            country=location["country"],
                            latitude=location["latitude"],
                            longitude=location["longitude"],
                            location_source="demo",
                            referrer_url="https://demo.brandwise.local/product"
                            if event_index == 0
                            else None,
                            language="en-US",
                            is_bot=False,
                            extra_data={"seed": SEED_NAME, "demo": True},
                        )
                    )

        if events:
            db.add_all(events)
            db.commit()
        return len(events), len(products)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    args = parse_args()
    try:
        organization_id = uuid.UUID(args.organization_id)
        created, products = seed(organization_id, args.days, args.events_per_day)
    except (ValueError, RuntimeError, SQLAlchemyError) as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1

    print(f"Created {created} QSeal demo scan events across {products} products.")
    print(
        "The operation is idempotent; running it again will not duplicate these events."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
