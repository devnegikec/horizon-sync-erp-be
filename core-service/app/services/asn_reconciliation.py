"""Pure ASN receiving reconciliation computation.

Encapsulates the decision logic shared by the ASN ``receiving-summary``
endpoint so it can be unit-tested without a database or HTTP client.

Coverage map:
- IN-WF-011 — Live ASN reconciliation: expected vs scanned per SKU with
  accepted/short/excess/damaged/hold/rejected classification.
- IN-WF-012 — Match receipt: ``reconciled`` status and
  ``ready_for_receipt_note`` when every line fully matches with no exceptions.
- IN-WF-013 — Partial receipt: ``partial`` status and ``is_partial_receipt``
  when some stock arrived while the ASN balance stays open.
"""

from __future__ import annotations

from typing import Any


def compute_asn_reconciliation(
    line_items_data: list[dict[str, Any]],
    active_scans_by_sku: dict[str, int] | None = None,
    unresolved_exception_count: int = 0,
    include_active_session: bool = False,
) -> dict[str, Any]:
    """Compute per-line status and ASN-level reconciliation state.

    Args:
        line_items_data: Output of ``AsnOrderRepository.get_receiving_summary`` —
            one dict per ASN line with ``expected_qty``, ``accepted_qty``,
            ``rejected_qty``, ``short_qty``, ``excess_qty``, ``damaged_qty``,
            ``hold_qty``, ``pending_qty`` and ``over_qty``.
        active_scans_by_sku: SKU → scanned quantity from the active inbound
            session. Only applied when ``include_active_session`` is True.
        unresolved_exception_count: Number of open / pending-approval
            inbound exceptions.
        include_active_session: Whether an active session's scans should be
            folded into scanned totals and pending quantities.

    Returns:
        Dict containing ``line_items`` (per-line status + quantities),
        ``matched_items``, ``partial_items``, ``not_received_items``,
        ``over_items``, quantity totals, ``reconciliation_status``,
        ``ready_for_receipt_note`` and ``is_partial_receipt``.
    """
    scans = active_scans_by_sku or {}

    line_items: list[dict[str, Any]] = []
    matched = partial = not_received = over = 0

    for li in line_items_data:
        expected = li["expected_qty"]
        accepted = li["accepted_qty"]
        rejected_q = li["rejected_qty"]
        short_q = li["short_qty"]
        excess_q = li["excess_qty"]
        damaged_q = li["damaged_qty"]
        hold_q = li["hold_qty"]
        pending_q = li["pending_qty"]

        finalized_physical_qty = accepted + rejected_q + excess_q + damaged_q + hold_q
        scanned_q = finalized_physical_qty + scans.get(li["sku"], 0)
        short_q = max(short_q, expected - scanned_q, 0)
        over_q = max(li["over_qty"], scanned_q - expected, 0)
        has_exception = any((rejected_q, excess_q, damaged_q, hold_q))

        if expected == 0:
            item_status = "not_applicable"
        elif over_q > 0:
            item_status = "over"
            over += 1
        elif has_exception:
            item_status = "exception"
        elif scanned_q == expected and short_q == 0:
            item_status = "matched"
            matched += 1
        elif scanned_q < expected or short_q > 0:
            if scanned_q == 0:
                item_status = "not_received"
                not_received += 1
            else:
                item_status = "partial"
                partial += 1
        else:
            item_status = "exception"

        line_items.append(
            {
                "asn_item_id": li["asn_item_id"],
                "item_id": li["item_id"],
                "sku": li["sku"],
                "item_name": li["item_name"],
                "expected_qty": expected,
                "scanned_qty": scanned_q,
                "accepted_qty": accepted,
                "rejected_qty": rejected_q,
                "short_qty": short_q,
                "excess_qty": excess_q,
                "damaged_qty": damaged_q,
                "hold_qty": hold_q,
                "pending_qty": short_q if include_active_session else pending_q,
                "over_qty": over_q,
                "status": item_status,
            }
        )

    expected_total = sum(li["expected_qty"] for li in line_items_data)
    scanned_total = sum(li["scanned_qty"] for li in line_items)
    accepted_total = sum(li["accepted_qty"] for li in line_items)
    rejected_total = sum(li["rejected_qty"] for li in line_items)
    short_total = sum(li["short_qty"] for li in line_items)
    excess_total = sum(li["excess_qty"] for li in line_items)
    damaged_total = sum(li["damaged_qty"] for li in line_items)
    hold_total = sum(li["hold_qty"] for li in line_items)
    pending_total = sum(li["pending_qty"] for li in line_items)
    over_total = sum(li["over_qty"] for li in line_items)

    has_exceptions = unresolved_exception_count > 0 or any(
        li["rejected_qty"]
        or li["excess_qty"]
        or li["damaged_qty"]
        or li["hold_qty"]
        or li["over_qty"]
        for li in line_items
    )

    ready_for_receipt_note = (
        bool(line_items) and matched == len(line_items) and not has_exceptions
    )

    if ready_for_receipt_note:
        reconciliation_status = "reconciled"
    elif has_exceptions:
        reconciliation_status = "exception"
    elif scanned_total > 0:
        reconciliation_status = "partial"
    else:
        reconciliation_status = "pending"

    return {
        "line_items": line_items,
        "matched_items": matched,
        "partial_items": partial,
        "not_received_items": not_received,
        "over_items": over,
        "expected_total_qty": expected_total,
        "scanned_total_qty": scanned_total,
        "accepted_total_qty": accepted_total,
        "rejected_total_qty": rejected_total,
        "short_total_qty": short_total,
        "excess_total_qty": excess_total,
        "damaged_total_qty": damaged_total,
        "hold_total_qty": hold_total,
        "pending_total_qty": pending_total,
        "over_total_qty": over_total,
        "has_exceptions": has_exceptions,
        "reconciliation_status": reconciliation_status,
        "ready_for_receipt_note": ready_for_receipt_note,
        "is_partial_receipt": reconciliation_status == "partial" and short_total > 0,
    }
