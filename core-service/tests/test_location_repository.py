"""Unit tests for LocationRepository"""

import uuid
from decimal import Decimal

import pytest

from app.models.warehouse_location import WarehouseLocation
from app.repositories.location_repository import LocationRepository


@pytest.fixture
def location_repo(db_session):
    """Create a LocationRepository instance with the test session."""
    return LocationRepository(db_session)


@pytest.fixture
def sample_warehouse_id():
    """A fixed warehouse UUID for testing."""
    return uuid.uuid4()


@pytest.fixture
def sample_org_id(mock_current_user):
    """Organization ID from the mock user."""
    return mock_current_user.organization_id


@pytest.fixture
def zone_location(db_session, sample_warehouse_id, sample_org_id):
    """Create a sample zone location."""
    loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=sample_org_id,
        warehouse_id=sample_warehouse_id,
        parent_location_id=None,
        location_type="zone",
        code="Z01",
        full_path="Z01",
        name="Receiving Zone",
        capacity=Decimal("0"),
        total_capacity=Decimal("1000"),
        available_capacity=Decimal("800"),
        is_active=True,
        version=1,
    )
    db_session.add(loc)
    db_session.commit()
    db_session.refresh(loc)
    return loc


@pytest.fixture
def aisle_location(db_session, sample_warehouse_id, sample_org_id, zone_location):
    """Create a sample aisle location under the zone."""
    loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=sample_org_id,
        warehouse_id=sample_warehouse_id,
        parent_location_id=zone_location.id,
        location_type="aisle",
        code="A01",
        full_path="Z01-A01",
        name="Aisle 01",
        capacity=Decimal("0"),
        total_capacity=Decimal("500"),
        available_capacity=Decimal("400"),
        is_active=True,
        version=1,
    )
    db_session.add(loc)
    db_session.commit()
    db_session.refresh(loc)
    return loc


@pytest.fixture
def bay_location(db_session, sample_warehouse_id, sample_org_id, aisle_location):
    """Create a sample bay location under the aisle."""
    loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=sample_org_id,
        warehouse_id=sample_warehouse_id,
        parent_location_id=aisle_location.id,
        location_type="bay",
        code="B01",
        full_path="Z01-A01-B01",
        name="Bay 01",
        capacity=Decimal("0"),
        total_capacity=Decimal("200"),
        available_capacity=Decimal("150"),
        is_active=True,
        version=1,
    )
    db_session.add(loc)
    db_session.commit()
    db_session.refresh(loc)
    return loc


class TestLocationRepositoryCreate:
    """Tests for the create method."""

    def test_create_location(self, location_repo, sample_warehouse_id, sample_org_id):
        """Test creating a new location."""
        data = {
            "organization_id": sample_org_id,
            "warehouse_id": sample_warehouse_id,
            "parent_location_id": None,
            "location_type": "zone",
            "code": "Z02",
            "full_path": "Z02",
            "name": "Storage Zone",
            "capacity": Decimal("0"),
            "total_capacity": Decimal("5000"),
            "available_capacity": Decimal("5000"),
            "is_active": True,
            "version": 1,
        }

        result = location_repo.create(data)

        assert result.id is not None
        assert result.code == "Z02"
        assert result.full_path == "Z02"
        assert result.location_type == "zone"
        assert result.organization_id == sample_org_id
        assert result.warehouse_id == sample_warehouse_id


class TestLocationRepositoryGetById:
    """Tests for the get_by_id method."""

    def test_get_existing_location(self, location_repo, zone_location, sample_org_id):
        """Test retrieving an existing location by ID."""
        result = location_repo.get_by_id(zone_location.id, sample_org_id)

        assert result is not None
        assert result.id == zone_location.id
        assert result.code == "Z01"

    def test_get_nonexistent_location(self, location_repo, sample_org_id):
        """Test retrieving a non-existent location returns None."""
        result = location_repo.get_by_id(uuid.uuid4(), sample_org_id)
        assert result is None

    def test_get_location_wrong_org(self, location_repo, zone_location):
        """Test that org_id filtering works - wrong org returns None."""
        result = location_repo.get_by_id(zone_location.id, uuid.uuid4())
        assert result is None


class TestLocationRepositoryUpdate:
    """Tests for the update method."""

    def test_update_location_name(self, location_repo, zone_location):
        """Test updating a location's name."""
        result = location_repo.update(zone_location.id, {"name": "Updated Zone"})

        assert result is not None
        assert result.name == "Updated Zone"

    def test_update_nonexistent_location(self, location_repo):
        """Test updating a non-existent location returns None."""
        result = location_repo.update(uuid.uuid4(), {"name": "Ghost"})
        assert result is None


class TestLocationRepositoryGetTree:
    """Tests for the get_tree method."""

    def test_get_tree_returns_hierarchy(
        self,
        location_repo,
        sample_warehouse_id,
        sample_org_id,
        zone_location,
        aisle_location,
        bay_location,
    ):
        """Test that get_tree returns all locations in the hierarchy."""
        result = location_repo.get_tree(sample_warehouse_id, sample_org_id)

        assert len(result) == 3
        # Should be ordered by full_path
        assert result[0].full_path == "Z01"
        assert result[1].full_path == "Z01-A01"
        assert result[2].full_path == "Z01-A01-B01"

    def test_get_tree_empty_warehouse(self, location_repo, sample_org_id):
        """Test get_tree for a warehouse with no locations."""
        result = location_repo.get_tree(uuid.uuid4(), sample_org_id)
        assert result == []


class TestLocationRepositoryListLocations:
    """Tests for the list_locations method."""

    def test_list_all_locations(
        self,
        location_repo,
        sample_org_id,
        zone_location,
        aisle_location,
        bay_location,
    ):
        """Test listing all locations for an org."""
        locations, total = location_repo.list_locations(sample_org_id)

        assert total == 3
        assert len(locations) == 3

    def test_list_with_type_filter(
        self,
        location_repo,
        sample_org_id,
        zone_location,
        aisle_location,
        bay_location,
    ):
        """Test filtering by location_type."""
        locations, total = location_repo.list_locations(
            sample_org_id, filters={"location_type": "zone"}
        )

        assert total == 1
        assert locations[0].location_type == "zone"

    def test_list_with_pagination(
        self,
        location_repo,
        sample_org_id,
        zone_location,
        aisle_location,
        bay_location,
    ):
        """Test pagination works correctly."""
        locations, total = location_repo.list_locations(
            sample_org_id, page=1, page_size=2
        )

        assert total == 3
        assert len(locations) == 2

    def test_list_with_active_filter(
        self,
        location_repo,
        sample_org_id,
        zone_location,
        aisle_location,
        bay_location,
        db_session,
    ):
        """Test filtering by is_active."""
        # Deactivate one location
        bay_location.is_active = False
        db_session.commit()

        locations, total = location_repo.list_locations(
            sample_org_id, filters={"is_active": True}
        )

        assert total == 2


class TestLocationRepositoryGetChildren:
    """Tests for the get_children method."""

    def test_get_children_of_zone(
        self, location_repo, sample_org_id, zone_location, aisle_location
    ):
        """Test getting direct children of a zone."""
        children = location_repo.get_children(zone_location.id, sample_org_id)

        assert len(children) == 1
        assert children[0].id == aisle_location.id

    def test_get_children_of_leaf(
        self, location_repo, sample_org_id, bay_location
    ):
        """Test getting children of a leaf node returns empty list."""
        children = location_repo.get_children(bay_location.id, sample_org_id)
        assert children == []


class TestLocationRepositoryGetDescendants:
    """Tests for the get_descendants method."""

    def test_get_all_descendants(
        self,
        location_repo,
        sample_org_id,
        zone_location,
        aisle_location,
        bay_location,
    ):
        """Test getting all descendants of a zone."""
        descendants = location_repo.get_descendants(zone_location.id, sample_org_id)

        assert len(descendants) == 2
        descendant_ids = {d.id for d in descendants}
        assert aisle_location.id in descendant_ids
        assert bay_location.id in descendant_ids

    def test_get_descendants_of_leaf(
        self, location_repo, sample_org_id, bay_location
    ):
        """Test getting descendants of a leaf node returns empty list."""
        descendants = location_repo.get_descendants(bay_location.id, sample_org_id)
        assert descendants == []


class TestLocationRepositorySearch:
    """Tests for the search method."""

    def test_search_by_code(
        self,
        location_repo,
        sample_warehouse_id,
        sample_org_id,
        zone_location,
        aisle_location,
    ):
        """Test searching by code."""
        results = location_repo.search(sample_warehouse_id, sample_org_id, "A01")

        assert len(results) == 1
        assert results[0].code == "A01"

    def test_search_by_name(
        self,
        location_repo,
        sample_warehouse_id,
        sample_org_id,
        zone_location,
    ):
        """Test searching by name."""
        results = location_repo.search(
            sample_warehouse_id, sample_org_id, "Receiving"
        )

        assert len(results) == 1
        assert results[0].name == "Receiving Zone"

    def test_search_by_full_path(
        self,
        location_repo,
        sample_warehouse_id,
        sample_org_id,
        zone_location,
        aisle_location,
        bay_location,
    ):
        """Test searching by full_path."""
        results = location_repo.search(
            sample_warehouse_id, sample_org_id, "Z01-A01"
        )

        # Should match aisle (Z01-A01) and bay (Z01-A01-B01)
        assert len(results) == 2

    def test_search_no_results(
        self, location_repo, sample_warehouse_id, sample_org_id, zone_location
    ):
        """Test search with no matching results."""
        results = location_repo.search(
            sample_warehouse_id, sample_org_id, "NONEXISTENT"
        )
        assert results == []


class TestLocationRepositoryDeactivateSubtree:
    """Tests for the deactivate_subtree method."""

    def test_deactivate_subtree(
        self,
        location_repo,
        zone_location,
        aisle_location,
        bay_location,
        db_session,
    ):
        """Test deactivating a zone deactivates all descendants."""
        count = location_repo.deactivate_subtree(zone_location.id)

        assert count == 3  # zone + aisle + bay

        # Refresh from DB
        db_session.refresh(zone_location)
        db_session.refresh(aisle_location)
        db_session.refresh(bay_location)

        assert zone_location.is_active is False
        assert aisle_location.is_active is False
        assert bay_location.is_active is False

    def test_deactivate_leaf(
        self,
        location_repo,
        zone_location,
        aisle_location,
        bay_location,
        db_session,
    ):
        """Test deactivating a leaf only deactivates itself."""
        count = location_repo.deactivate_subtree(bay_location.id)

        assert count == 1

        db_session.refresh(zone_location)
        db_session.refresh(aisle_location)
        db_session.refresh(bay_location)

        assert zone_location.is_active is True
        assert aisle_location.is_active is True
        assert bay_location.is_active is False

    def test_deactivate_increments_version(
        self,
        location_repo,
        zone_location,
        aisle_location,
        bay_location,
        db_session,
    ):
        """Test that deactivation increments the version column."""
        original_version = zone_location.version

        location_repo.deactivate_subtree(zone_location.id)

        db_session.refresh(zone_location)
        assert zone_location.version == original_version + 1
