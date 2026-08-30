"""Unit tests for the ERP sync outbound queue (PR-13 / T-13, WF-022, ALT-009).

Positive: a successful delivery dequeues the message (status ``sent``);
enqueueing the same entity/operation twice does not duplicate the queue.
Negative: a failing transport retries with backoff and, once the retry budget
is exhausted, marks the message failed and raises an in-app failure alert.

Uses a lightweight fake session (no DB fixture), matching PR-02..12 tests.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.erp_sync_message import ErpSyncMessage, ErpSyncStatus
from app.models.notification import Notification
from app.services.erp_sync_service import ErpSyncService


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
def user_id():
    return uuid.uuid4()


def _failing_transport():
    def _raise(message):
        raise RuntimeError("ERP down")

    return _raise


class TestEnqueue:
    def test_enqueue_creates_pending_message(self, org_id, user_id):
        db = _FakeDb()
        svc = ErpSyncService(db, max_retries=3, backoff_minutes=1)

        message = svc.enqueue(
            org_id, "pick_list", uuid.uuid4(), "status_update", user_id=user_id
        )

        assert message.status == ErpSyncStatus.PENDING.value
        assert message.attempt_count == 0
        assert message.max_attempts == 3

    def test_enqueue_dedups_pending(self, org_id, user_id):
        db = _FakeDb()
        svc = ErpSyncService(db, max_retries=3, backoff_minutes=1)
        entity_id = uuid.uuid4()

        first = svc.enqueue(org_id, "pick_list", entity_id, "status_update", user_id=user_id)
        second = svc.enqueue(org_id, "pick_list", entity_id, "status_update", user_id=user_id)

        assert first.id == second.id
        assert len(db.query(ErpSyncMessage).all()) == 1


class TestFlush:
    def test_successful_sync_dequeues(self, org_id, user_id):
        db = _FakeDb()
        svc = ErpSyncService(db, max_retries=3, backoff_minutes=1)
        message = svc.enqueue(
            org_id, "pick_list", uuid.uuid4(), "status_update", user_id=user_id
        )

        result = svc.flush_pending(org_id, now=datetime(2026, 8, 30, 12, 0, tzinfo=UTC))

        assert result == {"processed": 1, "sent": 1, "retried": 0, "failed": 0}
        assert message.status == ErpSyncStatus.SENT.value
        assert message.sent_at is not None

    def test_failure_retries_then_alerts(self, org_id, user_id):
        db = _FakeDb()
        svc = ErpSyncService(
            db, transport=_failing_transport(), max_retries=2, backoff_minutes=1
        )
        message = svc.enqueue(
            org_id, "pick_list", uuid.uuid4(), "status_update", user_id=user_id
        )
        t0 = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)

        first = svc.flush_pending(org_id, now=t0)
        assert first == {"processed": 1, "sent": 0, "retried": 1, "failed": 0}
        assert message.status == ErpSyncStatus.PENDING.value
        assert message.attempt_count == 1
        assert message.next_attempt_at == t0 + timedelta(minutes=1)

        second = svc.flush_pending(org_id, now=t0 + timedelta(minutes=2))
        assert second == {"processed": 1, "sent": 0, "retried": 0, "failed": 1}
        assert message.status == ErpSyncStatus.FAILED.value
        assert message.attempt_count == 2

        alerts = db.query(Notification).all()
        assert len(alerts) == 1
        assert alerts[0].type == "erp_sync_failed"
        assert alerts[0].user_id == user_id

    def test_retry_not_due_is_skipped(self, org_id, user_id):
        db = _FakeDb()
        svc = ErpSyncService(
            db, transport=_failing_transport(), max_retries=3, backoff_minutes=1
        )
        svc.enqueue(org_id, "pick_list", uuid.uuid4(), "status_update", user_id=user_id)
        t0 = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)

        svc.flush_pending(org_id, now=t0)  # attempt 1, next attempt in 1 min
        second = svc.flush_pending(org_id, now=t0)  # not due yet

        assert second == {"processed": 0, "sent": 0, "retried": 0, "failed": 0}
