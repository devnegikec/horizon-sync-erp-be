"""Unit tests for the ASN-2026-00014 RCA stock-reversal fixes.

These cover the pure decision logic of the reject-time stock reversal without a
database:

- ``InboundService._reverse_stock_effects`` (fix 7.1) — the shared reversal used
  by ``reject_slip`` and ``reject_slip_item``.
- ``InboundService._cross_asn_scan_warning`` (fix 7.4) — early no-ASN exit.

See ``RCA_ASN-2026-00014_RECEIVING_COUNT_MISMATCH.md``.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.bin_stock_service import BinStockService
from app.services.inbound_service import InboundService


@pytest.fixture
def service():
    """InboundService with a mocked DB session (no real queries needed)."""
    db = MagicMock()
    return InboundService(db)


def _tracking(**overrides):
    base = {
        "id": uuid.uuid4(),
        "stock_entered": True,
        "stock_location_id": uuid.uuid4(),
        "item_id": uuid.uuid4(),
        "quantity": 2,
        "batch_number": "SER-1",
        "receiving_status": "damaged",
        "stock_entered_at": object(),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestReverseStockEffects:
    """Fix 7.1 — rejecting a slip/line must reverse the stock it created."""

    def test_removes_stock_detaches_tracking_and_closes_exception(
        self, service, monkeypatch
    ):
        calls = []

        def fake_remove_stock(self, **kwargs):
            calls.append(kwargs)

        monkeypatch.setattr(BinStockService, "remove_stock", fake_remove_stock)

        tracking = _tracking()
        stripped_location = tracking.stock_location_id
        exception = SimpleNamespace(status="pending_approval")
        org_id = uuid.uuid4()

        reversed_count = service._reverse_stock_effects([tracking], [exception], org_id)

        assert reversed_count == 1
        # Stock removed from the exact location the tracking owned, without
        # committing mid-way.
        assert len(calls) == 1
        assert calls[0]["bin_id"] == stripped_location
        assert calls[0]["item_id"] == tracking.item_id
        assert calls[0]["batch_number"] == "SER-1"
        assert calls[0]["commit"] is False
        # Tracking detached and marked rejected so the identity can be re-scanned.
        assert tracking.stock_entered is False
        assert tracking.stock_location_id is None
        assert tracking.stock_entered_at is None
        assert tracking.receiving_status == "rejected"
        # Exception closed so it stops surfacing as pending work.
        assert exception.status == "cancelled"
        service.db.flush.assert_called()

    def test_skips_tracking_without_entered_stock(self, service, monkeypatch):
        calls = []
        monkeypatch.setattr(
            BinStockService, "remove_stock", lambda self, **kw: calls.append(kw)
        )

        no_stock = _tracking(stock_entered=False, stock_location_id=None)
        count = service._reverse_stock_effects([no_stock], [], uuid.uuid4())

        assert count == 0
        assert calls == []

    def test_does_not_reopen_already_final_exception(self, service, monkeypatch):
        monkeypatch.setattr(BinStockService, "remove_stock", lambda self, **kw: None)

        closed = SimpleNamespace(status="closed")
        released = SimpleNamespace(status="released")
        cancelled = SimpleNamespace(status="cancelled")

        service._reverse_stock_effects([], [closed, released, cancelled], uuid.uuid4())

        assert closed.status == "closed"
        assert released.status == "released"
        assert cancelled.status == "cancelled"


class TestCrossAsnScanWarning:
    """Fix 7.4 — warn (non-blocking) when a serial belongs to another ASN."""

    def test_no_warning_when_session_has_no_asn(self, service):
        session = SimpleNamespace(asn_order_id=None)
        assert (
            service._cross_asn_scan_warning(
                qr_identifier="SER-1",
                session=session,
                organization_id=uuid.uuid4(),
            )
            is None
        )

    def test_warning_shape(self, service):
        warning = service._wrong_asn_warning("SER-1", uuid.uuid4(), "ASN-2026-00001")
        assert warning["type"] == "wrong_asn"
        assert warning["qr_identifier"] == "SER-1"
        assert warning["expected_asn_order_no"] == "ASN-2026-00001"
        assert "ASN-2026-00001" in warning["message"]
