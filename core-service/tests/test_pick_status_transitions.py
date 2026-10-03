"""Unit tests for inventory movement status transitions (PR-08 / T-09, WF-016).

Positive: a valid ``available → picked → in_transit_to_stage`` transition
applies and is audited; a same-status call is an idempotent no-op.
Negative: an invalid transition is rejected; a replayed movement does not
double-post.

Uses a lightweight fake session (no DB fixture), matching PR-02..07 tests.
"""

import uuid
from decimal import Decimal

import pytest

from app.core.exceptions import ValidationError
from app.models.bin_stock_level import (
    InventoryStatus,
    can_transition_inventory_status,
)
from app.models.status_transition import StatusTransition
from app.models.stock_movement import StockMovement
from app.services.bin_stock_service import BinStockService

# ---------------------------------------------------------------------------
# Minimal fake session (equality filters only).
# ---------------------------------------------------------------------------

class _FakeQuery:
    def __init__(self, rows, criteria=()):
        self._rows = list(rows)
        self._criteria = list(criteria)

    def filter(self, *criteria):
        return _FakeQuery(self._rows, self._criteria + list(criteria))

    def _matching(self):
        return [r for r in self._rows if all(_matches(r, c) for c in self._criteria)]

    def all(self):
        return self._matching()

    def first(self):
        rows = self._matching()
        return rows[0] if rows else None


def _matches(row, criterion):
    if criterion is None:
        return True
    left = getattr(criterion, "left", None)
    right = getattr(criterion, "right", None)
    if left is None or right is None:
        return True
    attr = getattr(left, "key", None) or getattr(left, "name", None)
    if attr is None:
        return True
    op_name = getattr(getattr(criterion, "operator", None), "__name__", "")
    value = right.value if hasattr(right, "value") else right
    row_value = getattr(row, attr, None)
    if op_name == "eq":
        return row_value == value
    if op_name == "ne":
        return row_value != value
    return True


class _FakeDb:
    def __init__(self, rows=None):
        self._rows = list(rows or [])

    def query(self, model):
        return _FakeQuery([r for r in self._rows if isinstance(r, model)])

    def add(self, obj):
        self._rows.append(obj)

    def flush(self):
        return None

    def commit(self):
        return None

    def refresh(self, obj):
        return None


@pytest.fixture
def org_id():
    return uuid.uuid4()


def _bin_stock(status=None):
    from app.models.bin_stock_level import BinStockLevel

    return BinStockLevel(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        bin_location_id=uuid.uuid4(),
        item_id=uuid.uuid4(),
        quantity_on_hand=Decimal("0"),
        inventory_status=status or InventoryStatus.AVAILABLE.value,
    )


# ---------------------------------------------------------------------------
# Pure state machine
# ---------------------------------------------------------------------------

class TestCanTransition:
    def test_pick_chain(self):
        assert can_transition_inventory_status("available", "picked") is True
        assert can_transition_inventory_status("picked", "in_transit_to_stage") is True

    def test_invalid_skips_rejected(self):
        assert can_transition_inventory_status("available", "in_transit_to_stage") is False
        assert can_transition_inventory_status("picked", "blocked") is False

    def test_same_status_allowed(self):
        assert can_transition_inventory_status("picked", "picked") is True

    def test_none_treated_as_available(self):
        assert can_transition_inventory_status(None, "picked") is True


# ---------------------------------------------------------------------------
# BinStockService.transition_status
# ---------------------------------------------------------------------------

class TestTransitionStatus:
    def test_valid_transition_applies_and_audits(self, org_id):
        db = _FakeDb()
        svc = BinStockService(db)
        bin_stock = _bin_stock("available")
        user_id = uuid.uuid4()

        result = svc.transition_status(bin_stock, "picked", user_id=user_id)
        assert result.inventory_status == "picked"
        transitions = [r for r in db._rows if isinstance(r, StatusTransition)]
        assert len(transitions) == 1
        assert transitions[0].previous_status == "available"
        assert transitions[0].new_status == "picked"

    def test_invalid_transition_rejected(self, org_id):
        svc = BinStockService(_FakeDb())
        bin_stock = _bin_stock("available")
        with pytest.raises(ValidationError, match="Invalid inventory status transition"):
            svc.transition_status(bin_stock, "in_transit_to_stage", user_id=uuid.uuid4())

    def test_same_status_is_idempotent_noop(self, org_id):
        db = _FakeDb()
        svc = BinStockService(db)
        bin_stock = _bin_stock("picked")

        svc.transition_status(bin_stock, "picked", user_id=uuid.uuid4())
        # Replay: same status → no new audit row.
        svc.transition_status(bin_stock, "picked", user_id=uuid.uuid4())
        transitions = [r for r in db._rows if isinstance(r, StatusTransition)]
        assert len(transitions) == 0


# ---------------------------------------------------------------------------
# BinStockService.record_pick_movement (idempotent ledger posting)
# ---------------------------------------------------------------------------

class TestRecordPickMovement:
    def test_posts_movement_once(self, org_id):
        db = _FakeDb()
        svc = BinStockService(db)
        ref = uuid.uuid4()

        first = svc.record_pick_movement(
            org_id=org_id,
            product_id=uuid.uuid4(),
            warehouse_id=uuid.uuid4(),
            quantity=Decimal("3"),
            reference_type="pick_scan",
            reference_id=ref,
        )
        assert first is not None

        # Replay with the same reference → no double-post.
        second = svc.record_pick_movement(
            org_id=org_id,
            product_id=uuid.uuid4(),
            warehouse_id=uuid.uuid4(),
            quantity=Decimal("3"),
            reference_type="pick_scan",
            reference_id=ref,
        )
        assert second is None
        movements = [r for r in db._rows if isinstance(r, StockMovement)]
        assert len(movements) == 1

    def test_different_reference_posts_again(self, org_id):
        db = _FakeDb()
        svc = BinStockService(db)

        svc.record_pick_movement(
            org_id=org_id,
            product_id=uuid.uuid4(),
            warehouse_id=uuid.uuid4(),
            quantity=Decimal("1"),
            reference_type="pick_scan",
            reference_id=uuid.uuid4(),
        )
        second = svc.record_pick_movement(
            org_id=org_id,
            product_id=uuid.uuid4(),
            warehouse_id=uuid.uuid4(),
            quantity=Decimal("1"),
            reference_type="pick_scan",
            reference_id=uuid.uuid4(),
        )
        assert second is not None
        movements = [r for r in db._rows if isinstance(r, StockMovement)]
        assert len(movements) == 2
