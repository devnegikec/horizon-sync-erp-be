"""Celery beat task: flag dispatched-but-unreceived transfer serials (T3.1)."""

import logging

from app import models as _models  # noqa: F401 - register every ORM mapper
from app.celery_app import celery_app
from app.config import settings
from app.database import SessionLocal
from app.services.transfer_reconciliation_service import (
    TransferReconciliationService,
)

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="transfer.reconcile_missing_serials",
    acks_late=True,
    reject_on_worker_lost=True,
)
def reconcile_missing_serials_task(self) -> dict:
    """Raise MISSING_SERIAL exceptions for stale unreceived transfer serials."""
    db = SessionLocal()
    try:
        service = TransferReconciliationService(db)
        result = service.reconcile_missing_serials(
            older_than_hours=settings.missing_serial_alert_hours,
        )
        logger.info("Missing-serial reconciliation complete: %s", result)
        return result
    except Exception:  # noqa: BLE001 - never take the worker down
        logger.exception("Missing-serial reconciliation failed")
        raise
    finally:
        db.close()
