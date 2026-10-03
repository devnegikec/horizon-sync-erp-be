"""Unit tests for short-pick / over-pick tolerance (PR-07 / T-08, WF-015, EX-002/021, ALT-004).

Positive: over-pick within tolerance accepted; short-pick within policy returns
the shortfall to record as an exception.
Negative: over-pick beyond tolerance blocked; short-pick disabled blocked;
short-pick above the approval threshold blocked.

Uses a lightweight fake session (no DB fixture), matching PR-02..06 tests.
"""

import uuid
from decimal import Decimal

import pytest

from app.core.exceptions import ValidationError
from app.models.pick_list import PickListItem
from app.models.pick_setting import PickSetting
from app.services.pick_list_service import PickListService

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


def _pick_item(qty, picked):
    return PickListItem(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        pick_list_id=uuid.uuid4(),
        qty=Decimal(str(qty)),
        picked_qty=Decimal(str(picked)),
    )


def _service(org_id, overrides):
    """Build a PickListService with seeded pick_settings overrides."""
    rows = [
        PickSetting(organization_id=org_id, key=key, value=value)
        for key, value in overrides.items()
    ]
    return PickListService(_FakeDb(rows))


class TestOverPickTolerance:
    def test_within_tolerance_accepted(self, org_id):
        svc = _service(org_id, {"over_pick_tolerance": 2})
        svc.validate_over_pick(org_id, Decimal("10"), Decimal("11"))  # no raise

    def test_beyond_tolerance_blocked(self, org_id):
        svc = _service(org_id, {"over_pick_tolerance": 0})
        with pytest.raises(ValidationError, match="Over-picking"):
            svc.validate_over_pick(org_id, Decimal("10"), Decimal("11"))

    def test_default_tolerance_is_zero(self, org_id):
        svc = _service(org_id, {})
        with pytest.raises(ValidationError, match="Over-picking"):
            svc.validate_over_pick(org_id, Decimal("10"), Decimal("10.001"))


class TestShortPickPolicy:
    def test_within_policy_returns_shortfall(self, org_id):
        svc = _service(org_id, {"allow_short_pick": True, "short_pick_approval_threshold": 5})
        item = _pick_item(qty=10, picked=8)
        assert svc.validate_short_pick(org_id, item) == Decimal("2")

    def test_short_pick_disabled_blocked(self, org_id):
        svc = _service(org_id, {"allow_short_pick": False})
        item = _pick_item(qty=10, picked=8)
        with pytest.raises(ValidationError, match="not allowed"):
            svc.validate_short_pick(org_id, item)

    def test_above_threshold_blocked(self, org_id):
        svc = _service(org_id, {"allow_short_pick": True, "short_pick_approval_threshold": 0})
        item = _pick_item(qty=10, picked=8)
        with pytest.raises(ValidationError, match="approval threshold"):
            svc.validate_short_pick(org_id, item)

    def test_fully_picked_returns_none(self, org_id):
        svc = _service(org_id, {})
        item = _pick_item(qty=10, picked=10)
        assert svc.validate_short_pick(org_id, item) is None
