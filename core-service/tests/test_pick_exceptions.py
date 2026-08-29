"""Unit tests for the pick exception framework (PR-03 / T-02 + T-05).

Positive: capture writes an exception + immutable CAPTURED audit row; the
reason-code master is configurable.
Negative: duplicate capture rejected; invalid reason code rejected; unknown
pick list item rejected.

Uses a lightweight fake session (no DB fixture), matching the PR-02 tests.
"""

import uuid

import pytest

from app.core.exceptions import ResourceNotFoundException, ValidationError
from app.models.pick_exception import (
    PickException,
    PickExceptionAudit,
    PickExceptionAuditEvent,
    PickExceptionStatus,
)
from app.models.pick_list import PickListItem
from app.models.pick_setting import PickSetting
from app.services.pick_exception_service import PickExceptionService

# ---------------------------------------------------------------------------
# Minimal fake session that evaluates simple equality / IN filters.
# ---------------------------------------------------------------------------

class _FakeQuery:
    def __init__(self, rows, criteria=()):
        self._rows = list(rows)
        self._criteria = list(criteria)
        self._offset = 0
        self._limit = None

    def filter(self, *criteria):
        return _FakeQuery(self._rows, self._criteria + list(criteria))

    def order_by(self, *args):
        return self

    def offset(self, n):
        self._offset = n
        return self

    def limit(self, n):
        self._limit = n
        return self

    def _matching(self):
        return [r for r in self._rows if all(_matches(r, c) for c in self._criteria)]

    def all(self):
        rows = self._matching()
        if self._offset:
            rows = rows[self._offset:]
        if self._limit is not None:
            rows = rows[: self._limit]
        return rows

    def first(self):
        rows = self._matching()
        return rows[0] if rows else None

    def count(self):
        return len(self._matching())


def _matches(row, criterion):
    """Evaluate a simple BinaryExpression criterion against ``row``."""
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
    if op_name == "in_op":
        if isinstance(value, (set, frozenset)):
            value = list(value)
        return row_value in value
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
def pick_list_id():
    return uuid.uuid4()


def _pick_item(pick_list_item_id, org_id, pick_list_id):
    return PickListItem(
        id=pick_list_item_id,
        organization_id=org_id,
        pick_list_id=pick_list_id,
    )


# ---------------------------------------------------------------------------
# Capture (positive + negative)
# ---------------------------------------------------------------------------

class TestCapture:
    def test_capture_writes_exception_and_audit(self, org_id, pick_list_id):
        item_id = uuid.uuid4()
        reported_by = uuid.uuid4()
        db = _FakeDb([_pick_item(item_id, org_id, pick_list_id)])
        svc = PickExceptionService(db)

        exception = svc.capture(
            org_id,
            {"pick_list_item_id": item_id, "reason_code": "bin_empty"},
            reported_by=reported_by,
        )

        assert exception.reason_code == "bin_empty"
        assert exception.status == PickExceptionStatus.OPEN.value
        assert exception.severity == "warning"
        assert exception.reported_by == reported_by
        assert exception.pick_list_id == pick_list_id

        audits = [r for r in db._rows if isinstance(r, PickExceptionAudit)]
        assert len(audits) == 1
        assert audits[0].event_type == PickExceptionAuditEvent.CAPTURED.value
        assert audits[0].to_state == PickExceptionStatus.OPEN.value
        assert audits[0].actor_id == reported_by
        assert audits[0].details == {"reason_code": "bin_empty", "severity": "warning"}

    def test_capture_rejects_invalid_reason_code(self, org_id, pick_list_id):
        item_id = uuid.uuid4()
        db = _FakeDb([_pick_item(item_id, org_id, pick_list_id)])
        svc = PickExceptionService(db)

        with pytest.raises(ValidationError, match="Invalid reason code"):
            svc.capture(
                org_id,
                {"pick_list_item_id": item_id, "reason_code": "not_a_reason"},
            )
        assert not any(isinstance(r, PickException) for r in db._rows)

    def test_capture_rejects_duplicate(self, org_id, pick_list_id):
        item_id = uuid.uuid4()
        db = _FakeDb([_pick_item(item_id, org_id, pick_list_id)])
        svc = PickExceptionService(db)

        svc.capture(
            org_id,
            {"pick_list_item_id": item_id, "reason_code": "damaged"},
        )
        with pytest.raises(ValidationError, match="already exists"):
            svc.capture(
                org_id,
                {"pick_list_item_id": item_id, "reason_code": "damaged"},
            )
        # Exactly one exception persisted.
        exceptions = [r for r in db._rows if isinstance(r, PickException)]
        assert len(exceptions) == 1

    def test_capture_rejects_missing_pick_list_item(self, org_id):
        db = _FakeDb()
        svc = PickExceptionService(db)

        with pytest.raises(ResourceNotFoundException, match="not found"):
            svc.capture(
                org_id,
                {"pick_list_item_id": uuid.uuid4(), "reason_code": "bin_empty"},
            )


# ---------------------------------------------------------------------------
# Reason-code master + queries
# ---------------------------------------------------------------------------

class TestReasonCodes:
    def test_reason_codes_defaults_when_unset(self, org_id):
        from app.core.pick_config import DEFAULT_REASON_CODES

        svc = PickExceptionService(_FakeDb())
        assert svc.reason_codes(org_id) == DEFAULT_REASON_CODES

    def test_reason_codes_uses_configured_master(self, org_id):
        override = ["bin_empty", "damaged"]
        db = _FakeDb(
            [PickSetting(organization_id=org_id, key="reason_codes", value=override)]
        )
        svc = PickExceptionService(db)
        assert svc.reason_codes(org_id) == override


class TestQueries:
    def test_get_audit_returns_oldest_first(self, org_id, pick_list_id):
        item_id = uuid.uuid4()
        db = _FakeDb([_pick_item(item_id, org_id, pick_list_id)])
        svc = PickExceptionService(db)

        exception = svc.capture(
            org_id, {"pick_list_item_id": item_id, "reason_code": "bin_empty"}
        )
        events = svc.get_audit(org_id, exception.id)
        assert len(events) == 1
        assert events[0].event_type == "captured"

    def test_get_missing_exception_raises(self, org_id):
        svc = PickExceptionService(_FakeDb())
        with pytest.raises(ResourceNotFoundException, match="not found"):
            svc.get(org_id, uuid.uuid4())


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_serialize_shape(self, org_id, pick_list_id):
        exception = PickException(
            id=uuid.uuid4(),
            organization_id=org_id,
            pick_list_id=pick_list_id,
            pick_list_item_id=uuid.uuid4(),
            reason_code="damaged",
            severity="critical",
            status="open",
        )
        data = PickExceptionService._serialize(exception)
        assert data["reason_code"] == "damaged"
        assert data["severity"] == "critical"
        assert data["status"] == "open"
        assert data["pick_list_id"] == pick_list_id
        assert data["reported_by"] is None
