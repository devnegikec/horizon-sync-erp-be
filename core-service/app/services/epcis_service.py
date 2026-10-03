"""EPCIS 2.0-style event building for serial chain of custody.

Lightweight mapping from ``SerialNoHistory`` rows to EPCIS-style JSON events
(ObjectEvent / TransactionEvent) so serialized transfers can be exported for
downstream traceability consumers.
"""

from datetime import datetime


def _iso(ts) -> str | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts.isoformat()
    return str(ts)


def _biz_step(transaction_type: str) -> str:
    return {
        "pick": "picking",
        "transfer_out": "shipping",
        "transfer_in": "receiving",
        "putaway": "storing",
        "transfer_cancelled": "shipping",
    }.get(transaction_type, transaction_type)


def _disposition(transaction_type: str) -> str:
    return {
        "pick": "in_progress",
        "transfer_out": "in_transit",
        "transfer_in": "in_progress",
        "putaway": "sellable_available",
        "transfer_cancelled": "inactive",
    }.get(transaction_type, "in_progress")


def _action(transaction_type: str) -> str:
    # A serial leaves the source on transfer_out, is observed in transit,
    # and is added at the destination on transfer_in.
    if transaction_type in {"transfer_out", "transfer_in", "putaway", "pick"}:
        return "ADD"
    if transaction_type == "transfer_cancelled":
        return "DELETE"
    return "OBSERVE"


# Vendor-neutral GS1 placeholders so the URN parses as a valid SGTIN class URN
# (``urn:epc:id:sgtin:<CompanyPrefix>.<ItemReference>.<Serial>``). Downstream
# consumers should substitute a real company prefix / item reference when a
# GTIN is available; the unit serial is preserved verbatim as the final part.
NEUTRAL_COMPANY_PREFIX = "0000000"
NEUTRAL_ITEM_REFERENCE = "0"


def serial_epc(serial_no: str) -> str:
    """Return a valid EPCIS SGTIN URN for a unit serial.

    Uses vendor-neutral company-prefix/item-reference placeholders to produce
    the three dot-separated SGTIN components. If a real GTIN is available it
    should be substituted; the serial is preserved verbatim as the serial
    component.
    """
    return (
        f"urn:epc:id:sgtin:{NEUTRAL_COMPANY_PREFIX}."
        f"{NEUTRAL_ITEM_REFERENCE}.{serial_no}"
    )


def build_events_for_serial(serial_no: str, history_rows: list) -> list[dict]:
    """Map ``SerialNoHistory`` rows for one serial to EPCIS events."""
    events = []
    for h in history_rows:
        event = {
            "type": "ObjectEvent",
            "eventTime": _iso(h.transaction_date),
            "eventTimeZoneOffset": "+00:00",
            "epcList": [serial_epc(serial_no)],
            "action": _action(h.transaction_type),
            "bizStep": _biz_step(h.transaction_type),
            "disposition": _disposition(h.transaction_type),
            "readPoint": {"id": str(h.from_warehouse_id)}
            if h.from_warehouse_id
            else None,
            "bizLocation": {"id": str(h.to_warehouse_id)}
            if h.to_warehouse_id
            else None,
            "bizTransactionList": [
                {
                    "type": "po",
                    "bizTransaction": str(h.transaction_id),
                }
            ]
            if h.transaction_id
            else [],
        }
        events.append(event)
    return events
