"""Unit tests for handling-unit association (PR-11 / T-11, WF-018).

Positive: a handling unit associates with a pick list item.
Negative: a duplicate handling unit (already on another item) is rejected;
an unknown handling unit is rejected; when ``pick.enable_handling_unit`` is
off, validation is skipped (legacy).

Uses a lightweight fake session (no DB fixture), matching PR-02..10 tests.
"""

import uuid

import pytest

from app.core.exceptions import ResourceNotFoundException, ValidationError
from app.models.handling_unit import HandlingUnit
from app.models.pick_list import PickListItem
from app.models.pick_setting import PickSetting
from app.services.pick_list_service import PickListService

# ---------------------------------------------------------------------------
# Minimal fake session (equality/inequality filters only).
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


def _hu(org_id, hu_id=None):
    return HandlingUnit(
        id=hu_id or uuid.uuid4(),
        organization_id=org_id,
        warehouse_id=uuid.uuid4(),
        code="TROLLEY-01",
        hu_type="trolley",
        status="active",
    )


def _item(org_id, handling_unit_id=None):
    return PickListItem(
        id=uuid.uuid4(),
        organization_id=org_id,
        pick_list_id=uuid.uuid4(),
        handling_unit_id=handling_unit_id,
    )


def _service(org_id, enable_handling_unit, rows=()):
    all_rows = list(rows)
    if enable_handling_unit is not None:
        all_rows.append(
            PickSetting(
                organization_id=org_id,
                key="enable_handling_unit",
                value=enable_handling_unit,
            )
        )
    return PickListService(_FakeDb(all_rows))


class TestValidateHandlingUnit:
    def test_flag_on_valid_hu_accepted(self, org_id):
        item = _item(org_id)
        hu = _hu(org_id)
        svc = _service(org_id, True, rows=[item, hu])
        svc.validate_handling_unit_assignment(org_id, item.id, hu.id)  # no raise

    def test_duplicate_hu_rejected(self, org_id):
        item = _item(org_id)
        hu = _hu(org_id)
        other_item = _item(org_id, handling_unit_id=hu.id)
        svc = _service(org_id, True, rows=[item, hu, other_item])
        with pytest.raises(ValidationError, match="already assigned"):
            svc.validate_handling_unit_assignment(org_id, item.id, hu.id)

    def test_unknown_hu_rejected(self, org_id):
        item = _item(org_id)
        svc = _service(org_id, True, rows=[item])
        with pytest.raises(ResourceNotFoundException, match="not found"):
            svc.validate_handling_unit_assignment(org_id, item.id, uuid.uuid4())

    def test_flag_off_skips_validation(self, org_id):
        item = _item(org_id)
        hu = _hu(org_id)
        other_item = _item(org_id, handling_unit_id=hu.id)
        svc = _service(org_id, False, rows=[item, hu, other_item])
        # Duplicate HU is tolerated when the flag is off.
        svc.validate_handling_unit_assignment(org_id, item.id, hu.id)


class TestAssignHandlingUnit:
    def test_assign_sets_handling_unit_id(self, org_id):
        item = _item(org_id)
        hu = _hu(org_id)
        svc = _service(org_id, True, rows=[item, hu])

        result = svc.assign_handling_unit(item.id, hu.id, org_id)
        assert result.handling_unit_id == hu.id

    def test_assign_missing_item_rejected(self, org_id):
        hu = _hu(org_id)
        svc = _service(org_id, True, rows=[hu])
        with pytest.raises(ResourceNotFoundException, match="not found"):
            svc.assign_handling_unit(uuid.uuid4(), hu.id, org_id)

    def test_assign_flag_off_rejected(self, org_id):
        item = _item(org_id)
        hu = _hu(org_id)
        svc = _service(org_id, False, rows=[item, hu])
        with pytest.raises(ValidationError, match="disabled"):
            svc.assign_handling_unit(item.id, hu.id, org_id)
