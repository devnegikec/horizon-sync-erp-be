"""Unit tests for the wrong-bin hard stop (PR-05 / T-06, WF-012 / ALT-001 / EX-003).

Positive: the correct source bin is accepted.
Negative: a wrong bin is blocked with a hard-stop ValidationError; a missing
bin scan is rejected when required; the ``pick.require_bin_scan`` flag off
restores legacy behaviour; lines with no assigned bin skip the check.

Uses a lightweight fake session (no DB fixture), matching PR-02/03/04 tests.
"""

import uuid

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


def _pick_item(bin_location_id):
    return PickListItem(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        pick_list_id=uuid.uuid4(),
        bin_location_id=bin_location_id,
    )


def _service_with_flag(org_id, require_bin_scan):
    """Build a PickListService backed by a fake db with an optional override."""
    rows = []
    if require_bin_scan is not None:
        rows.append(
            PickSetting(
                organization_id=org_id,
                key="require_bin_scan",
                value=require_bin_scan,
            )
        )
    return PickListService(_FakeDb(rows))


class TestValidateBin:
    def test_correct_bin_accepted(self, org_id):
        bin_id = uuid.uuid4()
        svc = _service_with_flag(org_id, require_bin_scan=True)
        # Should not raise.
        svc.validate_bin(org_id, _pick_item(bin_id), bin_id)

    def test_wrong_bin_blocked(self, org_id):
        assigned = uuid.uuid4()
        scanned = uuid.uuid4()
        svc = _service_with_flag(org_id, require_bin_scan=True)
        with pytest.raises(ValidationError, match="Wrong bin"):
            svc.validate_bin(org_id, _pick_item(assigned), scanned)

    def test_missing_bin_scan_blocked(self, org_id):
        assigned = uuid.uuid4()
        svc = _service_with_flag(org_id, require_bin_scan=True)
        with pytest.raises(ValidationError, match="Bin scan required"):
            svc.validate_bin(org_id, _pick_item(assigned), None)

    def test_flag_off_allows_legacy_behaviour(self, org_id):
        assigned = uuid.uuid4()
        scanned = uuid.uuid4()
        svc = _service_with_flag(org_id, require_bin_scan=False)
        # Wrong bin is tolerated when the flag is off.
        svc.validate_bin(org_id, _pick_item(assigned), scanned)

    def test_no_assigned_bin_skips_validation(self, org_id):
        svc = _service_with_flag(org_id, require_bin_scan=True)
        # A line with no source bin has nothing to validate against.
        svc.validate_bin(org_id, _pick_item(None), None)

    def test_default_requires_bin_scan(self, org_id):
        # With no override row, the catalog default (true) applies.
        assigned = uuid.uuid4()
        svc = _service_with_flag(org_id, require_bin_scan=None)
        with pytest.raises(ValidationError, match="Bin scan required"):
            svc.validate_bin(org_id, _pick_item(assigned), None)
