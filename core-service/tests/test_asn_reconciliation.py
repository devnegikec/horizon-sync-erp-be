"""Unit tests for ASN receiving reconciliation logic.

Covers (without a database or HTTP client):
- IN-WF-011 — Live ASN reconciliation (expected vs scanned per SKU with
  short/excess/damaged/hold/rejected classification).
- IN-WF-012 — Match receipt (``reconciled`` state / ready for receipt note).
- IN-WF-013 — Partial receipt (``partial`` state / open ASN balance).
"""

from app.services.asn_reconciliation import compute_asn_reconciliation


def _line(
    *,
    asn_item_id: str = "ai-1",
    item_id: str = "item-1",
    sku: str = "SKU-A",
    item_name: str = "Widget",
    expected: int = 10,
    accepted: int = 0,
    rejected: int = 0,
    short: int = 0,
    excess: int = 0,
    damaged: int = 0,
    hold: int = 0,
    pending: int | None = None,
    over: int = 0,
) -> dict:
    """Build one line-item dict in the shape returned by get_receiving_summary."""
    if pending is None:
        pending = expected - (accepted + rejected + excess + damaged + hold)
    return {
        "asn_item_id": asn_item_id,
        "item_id": item_id,
        "sku": sku,
        "item_name": item_name,
        "expected_qty": expected,
        "accepted_qty": accepted,
        "rejected_qty": rejected,
        "short_qty": short,
        "excess_qty": excess,
        "damaged_qty": damaged,
        "hold_qty": hold,
        "pending_qty": pending,
        "over_qty": over,
    }


class TestLiveAsnReconciliation:
    """IN-WF-011 — live expected vs scanned reconciliation per line."""

    def test_partial_line_computes_short_and_scanned(self):
        result = compute_asn_reconciliation([_line(expected=10, accepted=6)])

        line = result["line_items"][0]
        assert line["status"] == "partial"
        assert line["scanned_qty"] == 6
        assert line["short_qty"] == 4
        assert result["short_total_qty"] == 4
        assert result["scanned_total_qty"] == 6

    def test_exception_line_classifies_damage_hold_rejected_and_over(self):
        lines = [
            _line(sku="SKU-A", expected=10, accepted=8, damaged=2),
            _line(sku="SKU-B", expected=10, accepted=8, hold=2),
            _line(sku="SKU-C", expected=3, accepted=2, rejected=1),
            _line(sku="SKU-D", expected=5, accepted=7),
        ]
        result = compute_asn_reconciliation(lines)

        statuses = {li["sku"]: li["status"] for li in result["line_items"]}
        assert statuses == {
            "SKU-A": "exception",
            "SKU-B": "exception",
            "SKU-C": "exception",
            "SKU-D": "over",
        }
        assert result["damaged_total_qty"] == 2
        assert result["hold_total_qty"] == 2
        assert result["rejected_total_qty"] == 1
        assert result["over_total_qty"] == 2
        assert result["over_items"] == 1

    def test_active_session_scans_fold_into_scanned_and_pending(self):
        result = compute_asn_reconciliation(
            [_line(expected=10)],
            active_scans_by_sku={"SKU-A": 4},
            include_active_session=True,
        )

        line = result["line_items"][0]
        assert line["scanned_qty"] == 4
        assert line["short_qty"] == 6
        # With an active session, pending reflects the live short balance.
        assert line["pending_qty"] == 6
        assert result["reconciliation_status"] == "partial"

    def test_active_scans_are_distributed_across_duplicate_sku_lines(self):
        lines = [
            _line(asn_item_id="ai-1", sku="SKU-A", expected=10),
            _line(asn_item_id="ai-2", sku="SKU-A", expected=10),
        ]
        result = compute_asn_reconciliation(
            lines,
            active_scans_by_sku={"SKU-A": 12},
            include_active_session=True,
        )

        by_id = {li["asn_item_id"]: li for li in result["line_items"]}
        assert by_id["ai-1"]["scanned_qty"] == 10
        assert by_id["ai-2"]["scanned_qty"] == 2
        assert result["scanned_total_qty"] == 12


class TestMatchReceipt:
    """IN-WF-012 — fully matched receipt becomes reconciled / ready."""

    def test_full_match_is_reconciled_and_ready(self):
        result = compute_asn_reconciliation([_line(expected=10, accepted=10)])

        assert result["matched_items"] == 1
        assert result["reconciliation_status"] == "reconciled"
        assert result["ready_for_receipt_note"] is True
        assert result["is_partial_receipt"] is False
        assert result["has_exceptions"] is False

    def test_exception_blocks_ready_for_receipt_note(self):
        lines = [
            _line(sku="SKU-A", expected=10, accepted=10),
            _line(sku="SKU-B", expected=5, accepted=4, damaged=1),
        ]
        result = compute_asn_reconciliation(lines)

        assert result["reconciliation_status"] == "exception"
        assert result["ready_for_receipt_note"] is False

    def test_unresolved_session_exception_blocks_reconciled(self):
        result = compute_asn_reconciliation(
            [_line(expected=10, accepted=10)],
            unresolved_exception_count=1,
        )

        assert result["reconciliation_status"] == "exception"
        assert result["ready_for_receipt_note"] is False


class TestPartialReceipt:
    """IN-WF-013 — partial arrival keeps the remaining ASN balance open."""

    def test_partial_arrival_keeps_open_balance(self):
        result = compute_asn_reconciliation([_line(expected=10, accepted=4)])

        assert result["reconciliation_status"] == "partial"
        assert result["is_partial_receipt"] is True
        assert result["short_total_qty"] == 6
        assert result["pending_total_qty"] == 6
        assert result["partial_items"] == 1
        assert result["ready_for_receipt_note"] is False

    def test_nothing_received_is_pending_not_partial(self):
        result = compute_asn_reconciliation([_line(expected=10)])

        line = result["line_items"][0]
        assert line["status"] == "not_received"
        assert result["reconciliation_status"] == "pending"
        assert result["is_partial_receipt"] is False
        assert result["not_received_items"] == 1

    def test_multi_line_partial_flags_partial_receipt(self):
        lines = [
            _line(sku="SKU-A", expected=10, accepted=10),
            _line(sku="SKU-B", expected=5, accepted=2),
        ]
        result = compute_asn_reconciliation(lines)

        assert result["reconciliation_status"] == "partial"
        assert result["is_partial_receipt"] is True
        assert result["matched_items"] == 1
        assert result["partial_items"] == 1
        assert result["short_total_qty"] == 3
