"""Unit tests for pick serial validation (PR-06 / T-07, WF-014 / EX-005/006 / ALT-003).

Positive: an available serial for the scanned SKU is accepted.
Negative: consumed/blocked serials rejected; a serial that does not belong to
the SKU rejected; a missing serial rejected when required. Policy ``per_item``
(default), ``never`` and ``always`` are all exercised.

Uses a lightweight fake session (no DB fixture), matching PR-02..05 tests.
"""

import uuid

import pytest

from app.core.exceptions import ValidationError
from app.models.item import Item
from app.models.pick_setting import PickSetting
from app.models.serial_no import SerialNo
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


def _item(has_serial_no=True):
    return Item(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        item_code="ITEM-001",
        item_name="Serialized Item",
        item_type="stock",
        uom="Nos",
        maintain_stock=True,
        has_serial_no=has_serial_no,
    )


def _serial(org_id, item_id, serial_no, status=None):
    return SerialNo(
        id=uuid.uuid4(),
        organization_id=org_id,
        serial_no=serial_no,
        item_id=item_id,
        warehouse_id=uuid.uuid4(),
        status=status,
    )


def _service(org_id, require_serial, rows=()):
    """Build a PickListService with an optional require_serial override."""
    all_rows = list(rows)
    if require_serial is not None:
        all_rows.append(
            PickSetting(
                organization_id=org_id, key="require_serial", value=require_serial
            )
        )
    return PickListService(_FakeDb(all_rows))


class TestValidateSerial:
    def test_available_serial_accepted(self, org_id):
        item = _item()
        svc = _service(org_id, None, rows=[_serial(org_id, item.id, "SN-001", "available")])
        svc.validate_serial(org_id, item, "SN-001")  # should not raise

    def test_consumed_serial_rejected(self, org_id):
        item = _item()
        svc = _service(org_id, None, rows=[_serial(org_id, item.id, "SN-001", "consumed")])
        with pytest.raises(ValidationError, match="consumed"):
            svc.validate_serial(org_id, item, "SN-001")

    def test_blocked_serial_rejected(self, org_id):
        item = _item()
        svc = _service(org_id, None, rows=[_serial(org_id, item.id, "SN-001", "blocked")])
        with pytest.raises(ValidationError, match="blocked"):
            svc.validate_serial(org_id, item, "SN-001")

    def test_wrong_sku_serial_rejected(self, org_id):
        item = _item()
        other_item_id = uuid.uuid4()
        # Serial exists but belongs to a different item.
        svc = _service(
            org_id, None, rows=[_serial(org_id, other_item_id, "SN-001", "available")]
        )
        with pytest.raises(ValidationError, match="not valid"):
            svc.validate_serial(org_id, item, "SN-001")

    def test_missing_serial_rejected(self, org_id):
        item = _item()
        svc = _service(org_id, None)
        with pytest.raises(ValidationError, match="Serial scan required"):
            svc.validate_serial(org_id, item, None)

    def test_per_item_skips_non_serialized(self, org_id):
        item = _item(has_serial_no=False)
        svc = _service(org_id, None)  # no SerialNo rows
        svc.validate_serial(org_id, item, "SN-UNKNOWN")  # should not raise

    def test_never_skips(self, org_id):
        item = _item()
        svc = _service(org_id, "never")
        svc.validate_serial(org_id, item, "SN-UNKNOWN")  # should not raise

    def test_always_enforces_even_non_serialized(self, org_id):
        item = _item(has_serial_no=False)
        svc = _service(org_id, "always")
        with pytest.raises(ValidationError, match="not valid"):
            svc.validate_serial(org_id, item, "SN-UNKNOWN")
