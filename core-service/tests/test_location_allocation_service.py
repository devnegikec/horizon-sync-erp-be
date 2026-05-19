"""Unit tests for LocationAllocationService."""

import uuid
from decimal import Decimal

import pytest

from app.core.exceptions import ValidationError
from app.models.location_allocation import LocationAllocation
from app.models.warehouse_location import WarehouseLocation
from app.services.location_allocation_service import LocationAllocationService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    return uuid.uuid4()


@pytest.fixture
def allocation_service(db_session):
    return LocationAllocationService(db_session)


def _create_location(
    db_session,
    org_id,
    warehouse_id,
    location_type="bin",
    code="B01",
    full_path=None,
    parent_id=None,
    is_active=True,
):
    """Helper to create a warehouse location directly in the DB."""
    loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=org_id,
        warehouse_id=warehouse_id,
        parent_location_id=parent_id,
        location_type=location_type,
        code=code,
        full_path=full_path or code,
        capacity=Decimal("100"),
        total_capacity=Decimal("100"),
        available_capacity=Decimal("100"),
        is_active=is_active,
        version=1,
    )
    db_session.add(loc)
    db_session.flush()
    return loc


class TestCreateAllocation:
    """Tests for create_allocation method."""

    def test_create_preferred_allocation(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should create a preferred allocation successfully."""
        location = _create_location(db_session, org_id, warehouse_id)
        item_group_id = uuid.uuid4()

        allocation = allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=item_group_id,
            organization_id=org_id,
            allocation_type="preferred",
            priority=5,
        )

        assert allocation.location_id == location.id
        assert allocation.item_group_id == item_group_id
        assert allocation.organization_id == org_id
        assert allocation.allocation_type == "preferred"
        assert allocation.priority == 5
        assert allocation.is_active is True

    def test_create_exclusive_allocation(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should create an exclusive allocation when no overlap exists."""
        location = _create_location(db_session, org_id, warehouse_id)
        item_group_id = uuid.uuid4()

        allocation = allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=item_group_id,
            organization_id=org_id,
            allocation_type="exclusive",
        )

        assert allocation.allocation_type == "exclusive"
        assert allocation.is_active is True

    def test_reject_exclusive_overlap(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should reject creating a second exclusive allocation on the same location."""
        location = _create_location(db_session, org_id, warehouse_id)
        item_group_1 = uuid.uuid4()
        item_group_2 = uuid.uuid4()

        # Create first exclusive allocation
        allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=item_group_1,
            organization_id=org_id,
            allocation_type="exclusive",
        )

        # Attempt second exclusive allocation on same location
        with pytest.raises(ValidationError, match="exclusive allocation already exists"):
            allocation_service.create_allocation(
                location_id=location.id,
                item_group_id=item_group_2,
                organization_id=org_id,
                allocation_type="exclusive",
            )

    def test_allow_preferred_after_exclusive(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should allow a preferred allocation even if an exclusive exists."""
        location = _create_location(db_session, org_id, warehouse_id)
        item_group_1 = uuid.uuid4()
        item_group_2 = uuid.uuid4()

        # Create exclusive allocation
        allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=item_group_1,
            organization_id=org_id,
            allocation_type="exclusive",
        )

        # Create preferred allocation on same location (should succeed)
        allocation = allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=item_group_2,
            organization_id=org_id,
            allocation_type="preferred",
        )

        assert allocation.allocation_type == "preferred"

    def test_reject_invalid_allocation_type(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should reject invalid allocation types."""
        location = _create_location(db_session, org_id, warehouse_id)

        with pytest.raises(ValidationError, match="Invalid allocation_type"):
            allocation_service.create_allocation(
                location_id=location.id,
                item_group_id=uuid.uuid4(),
                organization_id=org_id,
                allocation_type="invalid",
            )

    def test_reject_nonexistent_location(
        self, db_session, allocation_service, org_id
    ):
        """Should reject allocation for a non-existent location."""
        with pytest.raises(ValidationError, match="not found"):
            allocation_service.create_allocation(
                location_id=uuid.uuid4(),
                item_group_id=uuid.uuid4(),
                organization_id=org_id,
                allocation_type="preferred",
            )

    def test_allow_exclusive_after_deactivated_exclusive(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should allow a new exclusive allocation if the existing one is deactivated."""
        location = _create_location(db_session, org_id, warehouse_id)
        item_group_1 = uuid.uuid4()
        item_group_2 = uuid.uuid4()

        # Create and deactivate first exclusive allocation
        alloc1 = allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=item_group_1,
            organization_id=org_id,
            allocation_type="exclusive",
        )
        allocation_service.deactivate_allocation(alloc1.id, org_id)

        # Create new exclusive allocation (should succeed)
        alloc2 = allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=item_group_2,
            organization_id=org_id,
            allocation_type="exclusive",
        )

        assert alloc2.allocation_type == "exclusive"
        assert alloc2.is_active is True


class TestUpdateAllocation:
    """Tests for update_allocation method."""

    def test_update_priority(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should update the priority field."""
        location = _create_location(db_session, org_id, warehouse_id)
        allocation = allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
            priority=1,
        )

        updated = allocation_service.update_allocation(
            allocation_id=allocation.id,
            organization_id=org_id,
            priority=10,
        )

        assert updated.priority == 10

    def test_update_allocation_type_to_exclusive(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should allow changing from preferred to exclusive if no overlap."""
        location = _create_location(db_session, org_id, warehouse_id)
        allocation = allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
            allocation_type="preferred",
        )

        updated = allocation_service.update_allocation(
            allocation_id=allocation.id,
            organization_id=org_id,
            allocation_type="exclusive",
        )

        assert updated.allocation_type == "exclusive"

    def test_reject_update_to_exclusive_with_overlap(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should reject changing to exclusive if another exclusive exists."""
        location = _create_location(db_session, org_id, warehouse_id)

        # Create an exclusive allocation
        allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
            allocation_type="exclusive",
        )

        # Create a preferred allocation on same location
        preferred = allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
            allocation_type="preferred",
        )

        # Try to change preferred to exclusive
        with pytest.raises(ValidationError, match="Cannot change to exclusive"):
            allocation_service.update_allocation(
                allocation_id=preferred.id,
                organization_id=org_id,
                allocation_type="exclusive",
            )

    def test_update_nonexistent_raises_error(
        self, db_session, allocation_service, org_id
    ):
        """Should raise ValidationError for non-existent allocation."""
        with pytest.raises(ValidationError, match="not found"):
            allocation_service.update_allocation(
                allocation_id=uuid.uuid4(),
                organization_id=org_id,
                priority=5,
            )


class TestDeactivateAllocation:
    """Tests for deactivate_allocation method."""

    def test_deactivate_sets_inactive(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should set is_active=False."""
        location = _create_location(db_session, org_id, warehouse_id)
        allocation = allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
        )

        result = allocation_service.deactivate_allocation(allocation.id, org_id)

        assert result.is_active is False

    def test_deactivate_nonexistent_raises_error(
        self, db_session, allocation_service, org_id
    ):
        """Should raise ValidationError for non-existent allocation."""
        with pytest.raises(ValidationError, match="not found"):
            allocation_service.deactivate_allocation(uuid.uuid4(), org_id)


class TestListAllocations:
    """Tests for list_allocations method."""

    def test_list_all_for_org(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should list all allocations for an organization."""
        loc1 = _create_location(
            db_session, org_id, warehouse_id, code="B01", full_path="Z01-A01-B01"
        )
        loc2 = _create_location(
            db_session, org_id, warehouse_id, code="B02", full_path="Z01-A01-B02"
        )

        allocation_service.create_allocation(
            location_id=loc1.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
        )
        allocation_service.create_allocation(
            location_id=loc2.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
        )

        result = allocation_service.list_allocations(organization_id=org_id)

        assert result["pagination"]["total"] == 2
        assert len(result["allocations"]) == 2

    def test_filter_by_item_group(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should filter by item_group_id."""
        location = _create_location(db_session, org_id, warehouse_id)
        group_1 = uuid.uuid4()
        group_2 = uuid.uuid4()

        allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=group_1,
            organization_id=org_id,
        )

        loc2 = _create_location(
            db_session, org_id, warehouse_id, code="B02", full_path="B02"
        )
        allocation_service.create_allocation(
            location_id=loc2.id,
            item_group_id=group_2,
            organization_id=org_id,
        )

        result = allocation_service.list_allocations(
            organization_id=org_id, item_group_id=group_1
        )

        assert result["pagination"]["total"] == 1
        assert result["allocations"][0].item_group_id == group_1

    def test_filter_by_is_active(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should filter by active status."""
        loc1 = _create_location(
            db_session, org_id, warehouse_id, code="B01", full_path="B01"
        )
        loc2 = _create_location(
            db_session, org_id, warehouse_id, code="B02", full_path="B02"
        )

        alloc1 = allocation_service.create_allocation(
            location_id=loc1.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
        )
        allocation_service.create_allocation(
            location_id=loc2.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
        )

        # Deactivate first
        allocation_service.deactivate_allocation(alloc1.id, org_id)

        result = allocation_service.list_allocations(
            organization_id=org_id, is_active=True
        )

        assert result["pagination"]["total"] == 1

    def test_filter_by_warehouse_id(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should filter by warehouse_id via location join."""
        other_warehouse_id = uuid.uuid4()

        loc1 = _create_location(
            db_session, org_id, warehouse_id, code="B01", full_path="B01"
        )
        loc2 = _create_location(
            db_session, org_id, other_warehouse_id, code="B02", full_path="B02"
        )

        allocation_service.create_allocation(
            location_id=loc1.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
        )
        allocation_service.create_allocation(
            location_id=loc2.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
        )

        result = allocation_service.list_allocations(
            organization_id=org_id, warehouse_id=warehouse_id
        )

        assert result["pagination"]["total"] == 1

    def test_filter_by_location_type(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should filter by location_type via location join."""
        bin_loc = _create_location(
            db_session, org_id, warehouse_id,
            location_type="bin", code="B01", full_path="B01"
        )
        bay_loc = _create_location(
            db_session, org_id, warehouse_id,
            location_type="bay", code="BAY01", full_path="BAY01"
        )

        allocation_service.create_allocation(
            location_id=bin_loc.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
        )
        allocation_service.create_allocation(
            location_id=bay_loc.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
        )

        result = allocation_service.list_allocations(
            organization_id=org_id, location_type="bin"
        )

        assert result["pagination"]["total"] == 1

    def test_pagination(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should support pagination."""
        for i in range(5):
            loc = _create_location(
                db_session, org_id, warehouse_id,
                code=f"B{i:02d}", full_path=f"B{i:02d}"
            )
            allocation_service.create_allocation(
                location_id=loc.id,
                item_group_id=uuid.uuid4(),
                organization_id=org_id,
            )

        result = allocation_service.list_allocations(
            organization_id=org_id, page=1, page_size=2
        )

        assert result["pagination"]["total"] == 5
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["page_size"] == 2
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_prev"] is False
        assert len(result["allocations"]) == 2


class TestCheckExclusiveOverlap:
    """Tests for check_exclusive_overlap method."""

    def test_no_overlap_when_empty(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should return False when no allocations exist."""
        location = _create_location(db_session, org_id, warehouse_id)

        result = allocation_service.check_exclusive_overlap(
            location_id=location.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
        )

        assert result is False

    def test_overlap_when_exclusive_exists(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should return True when an active exclusive allocation exists."""
        location = _create_location(db_session, org_id, warehouse_id)

        allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
            allocation_type="exclusive",
        )

        result = allocation_service.check_exclusive_overlap(
            location_id=location.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
        )

        assert result is True

    def test_no_overlap_when_only_preferred(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should return False when only preferred allocations exist."""
        location = _create_location(db_session, org_id, warehouse_id)

        allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
            allocation_type="preferred",
        )

        result = allocation_service.check_exclusive_overlap(
            location_id=location.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
        )

        assert result is False

    def test_no_overlap_when_exclusive_is_inactive(
        self, db_session, allocation_service, org_id, warehouse_id
    ):
        """Should return False when the exclusive allocation is deactivated."""
        location = _create_location(db_session, org_id, warehouse_id)

        alloc = allocation_service.create_allocation(
            location_id=location.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
            allocation_type="exclusive",
        )
        allocation_service.deactivate_allocation(alloc.id, org_id)

        result = allocation_service.check_exclusive_overlap(
            location_id=location.id,
            item_group_id=uuid.uuid4(),
            organization_id=org_id,
        )

        assert result is False
