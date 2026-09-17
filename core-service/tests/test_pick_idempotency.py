"""Unit tests for pick idempotency (PR-04 / T-04, NFR-003 + EX-017).

Positive: same key replays the stored response without re-execution;
deterministic server-side derivation works when the caller omits the key.
Negative: different key creates a new transaction; a missing key derives a
stable key from task + payload.

Uses a lightweight fake session (no DB fixture), matching PR-02/PR-03 tests.
"""

import uuid

import pytest

from app.models.pick_idempotency import PickIdempotencyKey
from app.services.pick_idempotency_service import (
    OPERATION_CANCEL,
    OPERATION_COMPLETE,
    OPERATION_SCAN,
    PickIdempotencyService,
)

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

    def count(self):
        return len(self._matching())


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
        self.added = []

    def query(self, model):
        return _FakeQuery([r for r in self._rows if isinstance(r, model)])

    def add(self, obj):
        self.added.append(obj)
        self._rows.append(obj)

    def commit(self):
        return None


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def pick_list_id():
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------

class TestDeriveKey:
    def test_scan_key_is_deterministic_and_payload_sensitive(self, pick_list_id):
        a = PickIdempotencyService.derive_key(OPERATION_SCAN, pick_list_id, '{"sku":"X","qty":1}')
        b = PickIdempotencyService.derive_key(OPERATION_SCAN, pick_list_id, '{"sku":"X","qty":1}')
        c = PickIdempotencyService.derive_key(OPERATION_SCAN, pick_list_id, '{"sku":"X","qty":2}')
        assert a == b
        assert a != c

    def test_terminal_operation_key_has_no_payload(self, pick_list_id):
        complete = PickIdempotencyService.derive_key(OPERATION_COMPLETE, pick_list_id)
        cancel = PickIdempotencyService.derive_key(OPERATION_CANCEL, pick_list_id)
        assert complete == f"complete:{pick_list_id}"
        assert cancel == f"cancel:{pick_list_id}"

    def test_request_hash(self):
        digest = PickIdempotencyService.request_hash("payload")
        assert digest is not None and len(digest) == 64
        assert PickIdempotencyService.request_hash(None) is None


# ---------------------------------------------------------------------------
# Replay / record
# ---------------------------------------------------------------------------

class TestRecordAndReplay:
    def _recorded(self, org_id, pick_list_id, operation, key, response):
        db = _FakeDb()
        svc = PickIdempotencyService(db)
        svc.record(org_id, operation, key, pick_list_id, None, response)
        return db, svc

    def test_same_key_replays_stored_response(self, org_id, pick_list_id):
        response = {"pick_list_id": str(pick_list_id), "scanned_qty": 1}
        db, svc = self._recorded(org_id, pick_list_id, OPERATION_SCAN, "k1", response)

        assert svc.get_replay(org_id, OPERATION_SCAN, "k1") == response
        # One row only — no duplicate on the same key.
        rows = [r for r in db._rows if isinstance(r, PickIdempotencyKey)]
        assert len(rows) == 1

    def test_record_upserts_same_key(self, org_id, pick_list_id):
        db, svc = self._recorded(org_id, pick_list_id, OPERATION_COMPLETE, "k1", {"a": 1})
        svc.record(org_id, OPERATION_COMPLETE, "k1", pick_list_id, None, {"a": 2})

        rows = [r for r in db._rows if isinstance(r, PickIdempotencyKey)]
        assert len(rows) == 1
        assert svc.get_replay(org_id, OPERATION_COMPLETE, "k1") == {"a": 2}

    def test_different_key_creates_new_transaction(self, org_id, pick_list_id):
        db = _FakeDb()
        svc = PickIdempotencyService(db)
        svc.record(org_id, OPERATION_SCAN, "k1", pick_list_id, None, {"qty": 1})
        svc.record(org_id, OPERATION_SCAN, "k2", pick_list_id, None, {"qty": 2})

        rows = [r for r in db._rows if isinstance(r, PickIdempotencyKey)]
        assert len(rows) == 2
        assert svc.get_replay(org_id, OPERATION_SCAN, "k1") == {"qty": 1}
        assert svc.get_replay(org_id, OPERATION_SCAN, "k2") == {"qty": 2}

    def test_replay_scoped_to_operation_and_org(self, org_id, pick_list_id):
        other_org = uuid.uuid4()
        db, svc = self._recorded(org_id, pick_list_id, OPERATION_SCAN, "k1", {"qty": 1})

        assert svc.get_replay(other_org, OPERATION_SCAN, "k1") is None
        assert svc.get_replay(org_id, OPERATION_COMPLETE, "k1") is None

    def test_missing_key_returns_none(self, org_id):
        svc = PickIdempotencyService(_FakeDb())
        assert svc.get_replay(org_id, OPERATION_SCAN, "does-not-exist") is None
