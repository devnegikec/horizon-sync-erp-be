"""Unit tests for prioritization + task aging (PR-12 / T-12, WF-007, ALT-011).

Positive: a higher manual priority sorts first; an earlier dispatch cutoff
sorts first when ``priority_fields`` includes ``cutoff``.
Negative: an aged task (age >= threshold) is flagged as aging; an unknown
pick list cannot be prioritized.

Uses a lightweight fake session (no DB fixture), matching PR-02..11 tests.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import ResourceNotFoundException
from app.models.pick_list import PickList
from app.services.pick_list_service import PickListService


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


def _pl(org_id, priority=0, cutoff=None, wave=None, route=None, created=None, sla=None):
    return PickList(
        id=uuid.uuid4(),
        organization_id=org_id,
        pick_list_no="PL-1",
        priority=priority,
        dispatch_cutoff=cutoff,
        wave=wave,
        route=route,
        sla_minutes=sla,
        created_at=created,
    )


class TestPrioritySort:
    def test_higher_priority_sorts_first(self, org_id):
        high = _pl(org_id, priority=10)
        low = _pl(org_id, priority=1)
        sorted_ids = [
            pl.id
            for pl in sorted(
                [low, high], key=lambda p: PickListService.priority_sort_key([], p)
            )
        ]
        assert sorted_ids == [high.id, low.id]

    def test_cutoff_earlier_sorts_first(self, org_id):
        now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
        later = _pl(org_id, cutoff=now + timedelta(hours=2))
        earlier = _pl(org_id, cutoff=now)
        sorted_ids = [
            pl.id
            for pl in sorted(
                [later, earlier],
                key=lambda p: PickListService.priority_sort_key(["cutoff"], p),
            )
        ]
        assert sorted_ids == [earlier.id, later.id]

    def test_priority_beats_cutoff(self, org_id):
        now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
        urgent = _pl(org_id, priority=9, cutoff=now + timedelta(hours=1))
        later_but_low = _pl(org_id, priority=1, cutoff=now)
        sorted_ids = [
            pl.id
            for pl in sorted(
                [later_but_low, urgent],
                key=lambda p: PickListService.priority_sort_key(["cutoff"], p),
            )
        ]
        assert sorted_ids == [urgent.id, later_but_low.id]


class TestAging:
    def test_aging_threshold_triggers_alert(self, org_id):
        now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
        aged = _pl(org_id, created=now - timedelta(minutes=121))
        fresh = _pl(org_id, created=now - timedelta(minutes=60))

        assert PickListService.aging_info(aged, 120, now=now)["is_aging"] is True
        assert PickListService.aging_info(fresh, 120, now=now)["is_aging"] is False

    def test_aging_uses_sla_override(self, org_id):
        now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
        # 30 minutes old: not aged under the 120m org threshold, but aged
        # under a per-task SLA of 20 minutes.
        task = _pl(org_id, created=now - timedelta(minutes=30), sla=20)
        info = PickListService.aging_info(task, 120, now=now)
        assert info["age_minutes"] == 30
        assert info["is_aging"] is True

    def test_no_created_at_not_aging(self, org_id):
        task = _pl(org_id)
        info = PickListService.aging_info(task, 120)
        assert info["is_aging"] is False


class TestUpdatePriority:
    def test_update_priority_sets_fields(self, org_id):
        pl = _pl(org_id, priority=0)
        svc = PickListService(_FakeDb([pl]))

        result = svc.update_priority(
            pl.id, {"priority": 5, "wave": "W1", "route": "R2"}, org_id
        )
        assert result.priority == 5
        assert result.wave == "W1"
        assert result.route == "R2"

    def test_update_priority_missing_rejected(self, org_id):
        svc = PickListService(_FakeDb([]))
        with pytest.raises(ResourceNotFoundException, match="not found"):
            svc.update_priority(uuid.uuid4(), {"priority": 5}, org_id)
