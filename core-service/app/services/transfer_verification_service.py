"""Transfer verification — per-serial status for an internal-transfer ASN.

Answers, in one read: "which units left the source warehouse, which arrived,
which are still in transit, which are missing, and which showed up that were
never expected." This is the backend for the dispatch-slip serial-match screen
(T2.1 in ``WMS_DISPATCH_SERIAL_MATCH_DESIGN.md``).

Read-only. Consumes ``asn_order_serial_lines`` (the expected list written at
dispatch), ``serial_no_history`` (custody), the QSeal parent/child hierarchy
(carton identity) and inbound exceptions (unexpected arrivals).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.asn_order import AsnOrder, AsnOrderSerialLine
from app.models.inbound_exception import InboundException
from app.models.item import Item
from app.models.qseal import QSealParameters, QSealTrack
from app.models.serial_no import SerialNoHistory


class TransferVerificationService:
    """Builds the per-serial transfer verification report for an ASN."""

    def __init__(self, db: Session):
        self.db = db

    def verification_report(self, asn_order_id: UUID, organization_id: UUID) -> dict:
        asn_order = (
            self.db.query(AsnOrder)
            .filter(
                AsnOrder.id == asn_order_id,
                AsnOrder.organization_id == organization_id,
            )
            .first()
        )
        if asn_order is None:
            raise NotFoundError(
                message="ASN order not found",
                entity_type="AsnOrder",
                entity_id=str(asn_order_id),
            )

        serial_lines = (
            self.db.query(AsnOrderSerialLine)
            .filter(
                AsnOrderSerialLine.asn_order_id == asn_order_id,
                AsnOrderSerialLine.organization_id == organization_id,
            )
            .order_by(AsnOrderSerialLine.created_at.asc())
            .all()
        )

        # Carton (QSeal parent) resolution: serial → parent track.
        serial_numbers = [line.serial_no for line in serial_lines]
        carton_by_serial: dict[str, dict] = {}
        if serial_numbers:
            params = (
                self.db.query(QSealParameters)
                .filter(
                    QSealParameters.serial_number.in_(serial_numbers),
                    QSealParameters.organization_id == organization_id,
                )
                .all()
            )
            parent_ids = {p.parent_id for p in params if p.parent_id}
            tracks: dict[UUID, QSealTrack] = {}
            if parent_ids:
                tracks = {
                    t.id: t
                    for t in self.db.query(QSealTrack)
                    .filter(QSealTrack.id.in_(parent_ids))
                    .all()
                }
            for param in params:
                track = tracks.get(param.parent_id) if param.parent_id else None
                carton_by_serial[param.serial_number] = {
                    "carton_id": str(track.id) if track else None,
                    "carton": track.name if track else None,
                    "carton_serial": track.serial_number if track else None,
                }

        # Item catalogue for the serial lines.
        item_ids = {line.item_id for line in serial_lines}
        items: dict[UUID, Item] = {}
        if item_ids:
            items = {
                i.id: i
                for i in self.db.query(Item)
                .filter(Item.id.in_(item_ids))
                .all()
            }

        # Unexpected arrivals: inbound exceptions recorded for this ASN when a
        # scanned serial was not on the expected list (or was the wrong item).
        unexpected_serials: dict[str, dict] = {}
        if asn_order.asn_type == "internal_transfer":
            unexpected_rows = (
                self.db.query(InboundException)
                .filter(
                    InboundException.asn_order_id == asn_order_id,
                    InboundException.organization_id == organization_id,
                    InboundException.exception_type.in_(
                        ("serial_not_in_asn", "wrong_item")
                    ),
                )
                .all()
            )
            for exc in unexpected_rows:
                if exc.qr_identifier and exc.qr_identifier not in unexpected_serials:
                    unexpected_serials[exc.qr_identifier] = {
                        "serial_no": exc.qr_identifier,
                        "sku": exc.sku,
                        "reason_code": exc.reason_code,
                        "exception_type": exc.exception_type,
                    }

        # Dispatched-at: earliest transfer_out custody record for the ASN.
        dispatched_at = (
            self.db.query(SerialNoHistory.transaction_date)
            .filter(
                SerialNoHistory.transaction_type == "transfer_out",
                SerialNoHistory.transaction_id == asn_order_id,
                SerialNoHistory.organization_id == organization_id,
            )
            .order_by(SerialNoHistory.transaction_date.asc())
            .first()
        )
        dispatched_at_value = dispatched_at[0] if dispatched_at else None

        # Past the expected delivery window → "missing" rather than "in_transit".
        now = datetime.now(UTC)
        past_delivery = (
            asn_order.delivery_date is not None and now > asn_order.delivery_date
        )

        serials: list[dict] = []
        cartons: dict[str, dict] = {}
        for line in serial_lines:
            item = items.get(line.item_id)
            carton = carton_by_serial.get(line.serial_no, {})
            if line.received:
                status = "received"
            elif past_delivery:
                status = "missing"
            else:
                status = "in_transit"

            serials.append(
                {
                    "serial_no": line.serial_no,
                    "item_id": str(line.item_id),
                    "item_code": item.item_code if item else None,
                    "sku": (item.sku or item.item_code) if item else None,
                    "item_name": item.item_name if item else None,
                    "carton_id": carton.get("carton_id"),
                    "carton": carton.get("carton"),
                    "carton_serial": carton.get("carton_serial"),
                    "status": status,
                    "received_at": line.received_at.isoformat()
                    if line.received_at
                    else None,
                    "received_by": str(line.received_by) if line.received_by else None,
                }
            )

            carton_key = carton.get("carton") or "__uncartoned__"
            rollup = cartons.setdefault(
                carton_key,
                {
                    "carton": carton.get("carton"),
                    "carton_serial": carton.get("carton_serial"),
                    "expected": 0,
                    "received": 0,
                    "in_transit": 0,
                    "missing": 0,
                    "missing_serials": [],
                },
            )
            rollup["expected"] += 1
            if status == "received":
                rollup["received"] += 1
            elif status == "missing":
                rollup["missing"] += 1
                rollup["missing_serials"].append(line.serial_no)
            else:
                rollup["in_transit"] += 1

        # Append unexpected arrivals to the per-serial list (they have no line).
        for entry in unexpected_serials.values():
            serials.append(
                {
                    "serial_no": entry["serial_no"],
                    "item_id": None,
                    "item_code": None,
                    "sku": entry.get("sku"),
                    "item_name": None,
                    "carton_id": None,
                    "carton": None,
                    "carton_serial": None,
                    "status": "unexpected",
                    "received_at": None,
                    "received_by": None,
                    "reason_code": entry.get("reason_code"),
                    "exception_type": entry.get("exception_type"),
                }
            )

        total = len(serial_lines)
        received = sum(1 for line in serial_lines if line.received)
        missing = sum(1 for s in serials if s["status"] == "missing")

        return {
            "asn_order_id": str(asn_order_id),
            "asn_order_no": asn_order.asn_order_no,
            "asn_type": asn_order.asn_type or "purchase",
            "serialization_mode": asn_order.serialization_mode,
            "warehouse_from": str(asn_order.warehouse_id_from)
            if asn_order.warehouse_id_from
            else None,
            "warehouse_to": str(asn_order.warehouse_id_to)
            if asn_order.warehouse_id_to
            else None,
            "delivery_date": asn_order.delivery_date.isoformat()
            if asn_order.delivery_date
            else None,
            "dispatched_at": dispatched_at_value.isoformat()
            if dispatched_at_value
            else None,
            "summary": {
                "total_serials": total,
                "received": received,
                "in_transit": total - received - missing,
                "missing": missing,
                "unexpected": len(unexpected_serials),
            },
            "serials": serials,
            "cartons": list(cartons.values()),
        }
