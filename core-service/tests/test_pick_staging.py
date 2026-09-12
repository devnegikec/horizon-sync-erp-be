"""Unit tests for staging lane + stage validation (PR-10 / T-10, WF-019/020, EX-019/020, ALT-008).

Positive: a staging lane (``location_type = 'staging'``) is accepted; a scan of
the assigned lane is accepted.
Negative: a non-staging location is rejected (staging unavailable); a missing
lane is rejected; a wrong-lane scan is rejected; a scan before transfer is
rejected.

Uses a lightweight fake session (no DB fixture), matching PR-02..09 tests.
"""

import uuid

import pytest

from app.core.exceptions import ValidationError
from app.models.pick_list import PickList
from app.models.warehouse_location import LocationType, WarehouseLocation
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


def _location(org_id, location_type):
    return WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=org_id,
        warehouse_id=uuid.uuid4(),
        location_type=location_type,
        code="STG01" if location_type == "staging" else "BIN01",
        is_pickable=location_type != "staging",
    )


def _pick_list(staging_location_id=None):
    return PickList(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        staging_location_id=staging_location_id,
    )


class TestLocationType:
    def test_staging_value(self):
        assert LocationType.STAGING.value == "staging"


class TestValidateStagingLane:
    def test_staging_lane_accepted(self, org_id):
        lane = _location(org_id, "staging")
        svc = PickListService(_FakeDb([lane]))
        assert svc.validate_staging_lane(org_id, lane.id) is lane

    def test_non_staging_location_rejected(self, org_id):
        bin_loc = _location(org_id, "bin")
        svc = PickListService(_FakeDb([bin_loc]))
        with pytest.raises(ValidationError, match="not a staging lane"):
            svc.validate_staging_lane(org_id, bin_loc.id)

    def test_missing_lane_rejected(self, org_id):
        svc = PickListService(_FakeDb())
        with pytest.raises(ValidationError, match="not found"):
            svc.validate_staging_lane(org_id, uuid.uuid4())


class TestValidateStageScan:
    def test_matching_lane_accepted(self):
        lane_id = uuid.uuid4()
        svc = PickListService(_FakeDb())
        svc.validate_stage_scan(_pick_list(staging_location_id=lane_id), lane_id)

    def test_wrong_lane_rejected(self):
        assigned = uuid.uuid4()
        scanned = uuid.uuid4()
        svc = PickListService(_FakeDb())
        with pytest.raises(ValidationError, match="Wrong staging lane"):
            svc.validate_stage_scan(_pick_list(staging_location_id=assigned), scanned)

    def test_not_transferred_rejected(self):
        svc = PickListService(_FakeDb())
        with pytest.raises(ValidationError, match="not been transferred"):
            svc.validate_stage_scan(_pick_list(staging_location_id=None), uuid.uuid4())
