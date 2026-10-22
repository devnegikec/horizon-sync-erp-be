"""One-off backfill: legacy ``qr_credit_balance`` → new ``credit_batches``.

Run this once per environment *before* switching the UI/QR generation from the
legacy `/qr-credits/*` APIs to the new `/account/credits` + `/internal/credits/*`
engine.

What it does
------------
For every organization with ``qr_credit_balance.balance_credits > 0`` it creates
one ``credit_batches`` row with ``source_type='legacy_balance'`` and
``source_id=<organization_id>`` (idempotent — re-running creates nothing), then
writes the matching ``grant`` ledger entry.

Usage
-----
    cd core-service
    PYTHONPATH=. ./.venv/bin/python scripts/backfill_legacy_qr_credits.py
    PYTHONPATH=. ./.venv/bin/python scripts/backfill_legacy_qr_credits.py --apply

Defaults to a dry run; pass ``--apply`` to write.

Caveat: legacy ``reserved_credits`` are intentionally NOT migrated. Let in-flight
old-system reservations finish (or be released) before switching, otherwise they
would be granted twice.
"""

import argparse
import logging
from datetime import UTC, datetime, timedelta

from app.database import SessionLocal
from app.models.qr_credit import QRCreditBalance
from app.services.credit_engine_service import CreditEngineService

logger = logging.getLogger("backfill_legacy_qr_credits")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the batches (default is a dry run)",
    )
    parser.add_argument(
        "--expires-in-days",
        type=int,
        default=365,
        help="Expiry for migrated legacy credits (default 365 days)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    db = SessionLocal()
    service = CreditEngineService(db)
    expires_at = datetime.now(UTC) + timedelta(days=args.expires_in_days)
    migrated = 0
    skipped = 0
    try:
        balances = (
            db.query(QRCreditBalance)
            .filter(QRCreditBalance.balance_credits > 0)
            .order_by(QRCreditBalance.organization_id)
            .all()
        )
        logger.info(
            "Found %d organization(s) with legacy credit balance", len(balances)
        )
        for balance in balances:
            existing = service.credit_repo.get_batch_by_source(
                balance.organization_id, "legacy_balance", balance.organization_id
            )
            if existing is not None:
                skipped += 1
                logger.info(
                    "skip %s (already migrated: batch %s)",
                    balance.organization_id,
                    existing.id,
                )
                continue
            logger.info(
                "%s legacy balance=%s reserved=%s -> batch of %s",
                balance.organization_id,
                balance.balance_credits,
                balance.reserved_credits,
                balance.balance_credits,
            )
            if args.apply:
                service.grant_batch(
                    organization_id=balance.organization_id,
                    source_type="legacy_balance",
                    source_id=balance.organization_id,
                    quantity=balance.balance_credits,
                    expires_at=expires_at,
                    reason="Legacy qr_credit_balance migration",
                )
            migrated += 1
        if not args.apply:
            logger.info(
                "DRY RUN: would migrate %d organization(s), skipped %d. "
                "Re-run with --apply.",
                migrated,
                skipped,
            )
        else:
            logger.info("Migrated %d organization(s), skipped %d", migrated, skipped)
    finally:
        db.close()


if __name__ == "__main__":
    main()
