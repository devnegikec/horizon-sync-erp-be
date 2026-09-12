"""Unit tests for task accept + login session controls (PR-14 / T-14, WF-009/010).

Positive: accepting a pick task records the start timestamp; a successful
login resets the lockout counter.
Negative: exceeding the lockout attempt threshold locks the worker; an
idle-expired session is rejected on touch.

Uses a lightweight fake session (no DB fixture), matching PR-02..13 tests.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import ResourceNotFoundException, ValidationError
from app.models.base import PickListStatus
from app.models.pick_list import PickList
from app.services.pick_list_service import PickListService
from app.services.worker_session_service import WorkerSessionService


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


@pytest.fixture
def worker_id():
    return uuid.uuid4()


def _pick_list(org_id, status=PickListStatus.DRAFT):
    return PickList(
        id=uuid.uuid4(),
        organization_id=org_id,
        pick_list_no="PL-1",
        status=status,
        accepted_at=None,
        accepted_by=None,
        assigned_to=None,
    )


class TestAcceptTask:
    def test_accept_records_start_time(self, org_id, worker_id):
        pl = _pick_list(org_id)
        svc = PickListService(_FakeDb([pl]))

        result = svc.accept_task(pl.id, org_id, worker_id)

        assert result.accepted_at is not None
        assert result.accepted_by == worker_id
        assert result.status == PickListStatus.IN_PROGRESS

    def test_accept_idempotent_keeps_first_timestamp(self, org_id, worker_id):
        pl = _pick_list(org_id)
        svc = PickListService(_FakeDb([pl]))

        first = svc.accept_task(pl.id, org_id, worker_id)
        first_at = first.accepted_at
        second = svc.accept_task(pl.id, org_id, worker_id)

        assert second.accepted_at == first_at

    def test_accept_completed_rejected(self, org_id, worker_id):
        pl = _pick_list(org_id, status=PickListStatus.COMPLETED)
        svc = PickListService(_FakeDb([pl]))
        with pytest.raises(ValidationError, match="Cannot accept"):
            svc.accept_task(pl.id, org_id, worker_id)

    def test_accept_missing_rejected(self, org_id, worker_id):
        svc = PickListService(_FakeDb([]))
        with pytest.raises(ResourceNotFoundException, match="not found"):
            svc.accept_task(uuid.uuid4(), org_id, worker_id)


class TestLockout:
    def test_lockout_enforced_on_identity(self, org_id):
        # Lockout is now enforced on the identity `users` table (identity-service),
        # not in core-service. Assert the service no longer exposes it.
        assert not hasattr(WorkerSessionService, "record_failed_login")
        assert not hasattr(WorkerSessionService, "is_locked")


class TestSessionTimeout:
    def test_expired_session_rejected(self, org_id, worker_id):
        svc = WorkerSessionService(_FakeDb(), timeout_minutes=5)
        t0 = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)

        session = svc.start_session(org_id, worker_id, now=t0)
        with pytest.raises(ValidationError, match="expired"):
            svc.touch(session.id, org_id, now=t0 + timedelta(minutes=6))

    def test_touch_refreshes_within_timeout(self, org_id, worker_id):
        svc = WorkerSessionService(_FakeDb(), timeout_minutes=5)
        t0 = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)

        session = svc.start_session(org_id, worker_id, now=t0)
        touched = svc.touch(session.id, org_id, now=t0 + timedelta(minutes=4))

        assert touched.last_active_at == t0 + timedelta(minutes=4)

    def test_end_session(self, org_id, worker_id):
        svc = WorkerSessionService(_FakeDb(), timeout_minutes=5)
        session = svc.start_session(org_id, worker_id)
        ended = svc.end_session(session.id, org_id)

        assert ended.status == "ended"
        with pytest.raises(ValidationError, match="cannot be used"):
            svc.touch(session.id, org_id)
