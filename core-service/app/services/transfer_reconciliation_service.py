"""Scheduled reconciliation of dispatched-but-unreceived transfer serials (T3.1).

Detects internal-transfer ASNs whose serials were dispatched more than N hours
ago and never received, and raises a ``MISSING_SERIAL`` inbound exception per
ASN (idempotent) so the shortage is owned in the exception queue and the
supervisors are notified.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.asn_order import AsnOrder, AsnOrderSerialLine
from app.models.inbound_exception import InboundException

logger = logging.getLogger(__name__)

#: Reason code seeded by migration 126 (T0.6).
MISSING_SERIAL_REASON = "MISSING_SERIAL"


class TransferReconciliationService:
    """Finds and flags missing serials on serialized internal transfers."""

    def __init__(self, db: Session):
        self.db = db

    def reconcile_missing_serials(self, older_than_hours: int = 72) -> dict:
        """Raise MISSING_SERIAL exceptions for stale unreceived transfer serials.

        Returns a summary dict with the ASNs processed and exceptions created.
        """
        cutoff = datetime.now(UTC) - timedelta(hours=older_than_hours)

        # Serialize concurrent runs so two workers cannot both find no existing
        # exception and insert duplicate open MISSING_SERIAL rows for one ASN.
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key)::bigint)"),
            {"key": "transfer:missing-serial-reconcile"},
        )

        rows = (
            self.db.query(AsnOrderSerialLine, AsnOrder)
            .join(AsnOrder, AsnOrder.id == AsnOrderSerialLine.asn_order_id)
            .filter(
                AsnOrder.asn_type == "internal_transfer",
                AsnOrderSerialLine.received.is_(False),
                AsnOrderSerialLine.created_at < cutoff,
            )
            .all()
        )

        missing_by_asn: dict[UUID, dict] = {}
        for line, asn in rows:
            status = asn.status.value if hasattr(asn.status, "value") else str(asn.status)
            if status not in {"confirmed", "partially_delivered"}:
                continue
            bucket = missing_by_asn.setdefault(
                asn.id,
                {"asn": asn, "serials": []},
            )
            bucket["serials"].append(line.serial_no)

        created = 0
        skipped = 0
        created_exceptions: list[tuple[InboundException, str]] = []
        for bucket in missing_by_asn.values():
            asn = bucket["asn"]
            serials = bucket["serials"]

            # Idempotency: skip ASNs that already carry an open MISSING_SERIAL.
            existing = (
                self.db.query(InboundException)
                .filter(
                    InboundException.asn_order_id == asn.id,
                    InboundException.reason_code == MISSING_SERIAL_REASON,
                    InboundException.status == "open",
                )
                .first()
            )
            if existing is not None:
                skipped += 1
                continue

            exception = InboundException(
                organization_id=asn.organization_id,
                warehouse_id=asn.warehouse_id_to,
                asn_order_id=asn.id,
                session_id=None,
                item_id=None,
                exception_type="missing_serial",
                reason_code=MISSING_SERIAL_REASON,
                status="open",
                condition_code="GOOD",
                destination=None,
                qr_identifier=f"ASN-{asn.asn_order_no}",
                sku=None,
                batch_number=None,
                quantity=len(serials),
                note=(
                    f"{len(serials)} serial(s) dispatched but never received "
                    f"(older than {older_than_hours}h)"
                ),
                raw_qr_data=None,
                metadata_json={"missing_serials": serials},
                created_by=None,
            )
            self.db.add(exception)
            self.db.flush()
            created += 1
            created_exceptions.append((exception, asn.asn_order_no))
            logger.info(
                "MISSING_SERIAL raised for ASN '%s' — %d serial(s)",
                asn.asn_order_no,
                len(serials),
            )

        self.db.commit()

        # Notify supervisors for the exceptions created by THIS run only, so a
        # later scheduled run does not re-notify the same ASN.
        from app.services.inbound_exception_service import InboundExceptionService

        notifier = InboundExceptionService(self.db)
        notified = 0
        for exception, asn_no in created_exceptions:
            notified += notifier.notify_supervisors(
                exception,
                title=f"Missing serials: ASN {asn_no}",
            )

        return {
            "asns_with_missing_serials": len(missing_by_asn),
            "exceptions_created": created,
            "exceptions_skipped_existing": skipped,
            "supervisors_notified": notified,
            "cutoff": cutoff.isoformat(),
        }
