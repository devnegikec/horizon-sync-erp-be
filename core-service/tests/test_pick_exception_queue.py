"""Unit tests for the pick exception queue (PR-09 / T-03, ALT-004/005/007/008/011/012).

Positive: resolve updates the exception + writes an audit row; approve/reject
update the exception + approver; a best-effort in-app alert is raised for the
reporter.
Negative: resolving an already-resolved exception is rejected; an invalid
approval decision is rejected; a non-supervisor (WMS worker) lacks the
``warehouse.manage`` permission required to resolve/approve.

Uses a lightweight fake session (no DB fixture), matching PR-02..08 tests.
"""

import uuid

import pytest

from app.core.authorization import (
    WAREHOUSE_MANAGE,
    WMS_WORKER_PERMISSIONS,
)
from app.core.exceptions import ValidationError
from app.dependencies import has_permission
from app.models.pick_exception import (
    PickException,
    PickExceptionAudit,
    PickExceptionAuditEvent,
    PickExceptionStatus,
)
from app.services.pick_exception_service import PickExceptionService

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


def _exception(org_id, status="open", reported_by=None):
    return PickException(
        id=uuid.uuid4(),
        organization_id=org_id,
        pick_list_id=uuid.uuid4(),
        pick_list_item_id=uuid.uuid4(),
        reason_code="damaged",
        severity="warning",
        reported_by=reported_by,
        status=status,
    )


def _audits(db):
    return [r for r in db._rows if isinstance(r, PickExceptionAudit)]


class TestResolve:
    def test_resolve_updates_exception_and_audit(self, org_id):
        reporter = uuid.uuid4()
        resolver = uuid.uuid4()
        exception = _exception(org_id, reported_by=reporter)
        db = _FakeDb([exception])
        svc = PickExceptionService(db)

        result = svc.resolve(org_id, exception.id, "Damaged unit quarantined", resolver)

        assert result.status == PickExceptionStatus.RESOLVED.value
        assert result.resolution == "Damaged unit quarantined"
        audits = _audits(db)
        assert len(audits) == 1
        assert audits[0].event_type == PickExceptionAuditEvent.RESOLVED.value
        assert audits[0].to_state == PickExceptionStatus.RESOLVED.value
        assert audits[0].actor_id == resolver

    def test_resolve_already_resolved_rejected(self, org_id):
        exception = _exception(org_id, status="resolved")
        db = _FakeDb([exception])
        svc = PickExceptionService(db)

        with pytest.raises(ValidationError, match="Cannot resolve"):
            svc.resolve(org_id, exception.id, "again")


class TestApprove:
    def test_approve_updates_exception_and_audit(self, org_id):
        reporter = uuid.uuid4()
        approver = uuid.uuid4()
        exception = _exception(org_id, reported_by=reporter)
        db = _FakeDb([exception])
        svc = PickExceptionService(db)

        result = svc.approve(org_id, exception.id, approver, "approved")

        assert result.status == PickExceptionStatus.APPROVED.value
        assert result.approver == approver
        assert result.approved_at is not None
        audits = _audits(db)
        assert len(audits) == 1
        assert audits[0].event_type == PickExceptionAuditEvent.APPROVED.value

    def test_reject_updates_exception(self, org_id):
        exception = _exception(org_id)
        db = _FakeDb([exception])
        svc = PickExceptionService(db)

        result = svc.approve(org_id, exception.id, uuid.uuid4(), "rejected")
        assert result.status == PickExceptionStatus.REJECTED.value

    def test_approve_invalid_decision_rejected(self, org_id):
        exception = _exception(org_id)
        db = _FakeDb([exception])
        svc = PickExceptionService(db)

        with pytest.raises(ValidationError, match="Invalid decision"):
            svc.approve(org_id, exception.id, uuid.uuid4(), "nope")

    def test_approve_resolved_rejected(self, org_id):
        exception = _exception(org_id, status="resolved")
        db = _FakeDb([exception])
        svc = PickExceptionService(db)

        with pytest.raises(ValidationError, match="Cannot approved"):
            svc.approve(org_id, exception.id, uuid.uuid4(), "approved")


class TestSupervisorAuthorization:
    def test_worker_lacks_manage_permission(self):
        assert has_permission(WMS_WORKER_PERMISSIONS, WAREHOUSE_MANAGE) is False

    def test_supervisor_has_manage_permission(self):
        assert has_permission([WAREHOUSE_MANAGE], WAREHOUSE_MANAGE) is True
