"""Unit tests for LayoutService."""

import uuid
from decimal import Decimal

import pytest

from app.models.bin_stock_level import BinStockLevel
from app.models.warehouse_location import WarehouseLocation
from app.services.layout_service import VALID_PARENT_TYPES, LayoutService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    return uuid.uuid4()


@pytest.fixture
def layout_service(db_session):
    return LayoutService(db_session)


def _create_location(
    db_session,
    org_id,
    warehouse_id,
    location_type,
    code,
    full_path=None,
    parent_id=None,
    capacity=0,
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
        capacity=Decimal(str(capacity)),
        total_capacity=Decimal(str(capacity)),
        available_capacity=Decimal(str(capacity)),
        is_active=is_active,
        version=1,
    )
    db_session.add(loc)
    db_session.flush()
    return loc


class TestCreateLocation:
    """Tests for create_location method."""

    def test_create_zone_without_parent(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Zones should be created without a parent_location_id."""
        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
            name="Receiving Zone",
        )

        assert zone.location_type == "zone"
        assert zone.code == "Z01"
        assert zone.full_path == "Z01"
        assert zone.parent_location_id is None
        assert zone.is_active is True

    def test_create_aisle_under_zone(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Aisles must be created under a zone."""
        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )

        aisle = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="aisle",
            code="A01",
            parent_location_id=zone.id,
        )

        assert aisle.location_type == "aisle"
        assert aisle.full_path == "Z01-A01"
        assert aisle.parent_location_id == zone.id

    def test_create_full_hierarchy(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Create a full zone -> aisle -> bay -> level -> bin hierarchy."""
        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )
        aisle = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="aisle",
            code="A03",
            parent_location_id=zone.id,
        )
        bay = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="bay",
            code="B02",
            parent_location_id=aisle.id,
        )
        level = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="level",
            code="L04",
            parent_location_id=bay.id,
        )
        bin_loc = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="bin",
            code="B01",
            parent_location_id=level.id,
            capacity=Decimal("100"),
        )

        assert bin_loc.full_path == "Z01-A03-B02-L04-B01"
        assert bin_loc.capacity == Decimal("100")

    def test_reject_zone_with_parent(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Zones must NOT have a parent_location_id."""
        from app.core.exceptions import ValidationError

        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )

        with pytest.raises(ValidationError, match="zone must not have a parent"):
            layout_service.create_location(
                warehouse_id=warehouse_id,
                organization_id=org_id,
                location_type="zone",
                code="Z02",
                parent_location_id=zone.id,
            )

    def test_reject_aisle_without_parent(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Aisles must have a parent of type zone."""
        from app.core.exceptions import ValidationError

        with pytest.raises(ValidationError, match="must have a parent location"):
            layout_service.create_location(
                warehouse_id=warehouse_id,
                organization_id=org_id,
                location_type="aisle",
                code="A01",
            )

    def test_reject_aisle_under_aisle(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Aisles must be under a zone, not another aisle."""
        from app.core.exceptions import ValidationError

        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )
        aisle = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="aisle",
            code="A01",
            parent_location_id=zone.id,
        )

        with pytest.raises(ValidationError, match="must have a zone as parent"):
            layout_service.create_location(
                warehouse_id=warehouse_id,
                organization_id=org_id,
                location_type="aisle",
                code="A02",
                parent_location_id=aisle.id,
            )

    def test_reject_invalid_location_type(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Invalid location types should be rejected."""
        from app.core.exceptions import ValidationError

        with pytest.raises(ValidationError, match="Invalid location_type"):
            layout_service.create_location(
                warehouse_id=warehouse_id,
                organization_id=org_id,
                location_type="shelf",
                code="S01",
            )

    def test_reject_duplicate_full_path(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Duplicate full_path within the same warehouse should be rejected."""
        from app.core.exceptions import ValidationError

        layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )

        with pytest.raises(ValidationError, match="already exists"):
            layout_service.create_location(
                warehouse_id=warehouse_id,
                organization_id=org_id,
                location_type="zone",
                code="Z01",
            )

    def test_reject_creation_under_deactivated_parent(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Cannot create locations under a deactivated parent."""
        from app.core.exceptions import ValidationError

        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )
        layout_service.deactivate_location(zone.id, org_id)

        with pytest.raises(ValidationError, match="deactivated parent"):
            layout_service.create_location(
                warehouse_id=warehouse_id,
                organization_id=org_id,
                location_type="aisle",
                code="A01",
                parent_location_id=zone.id,
            )


class TestGenerateLocationCode:
    """Tests for location code generation."""

    def test_zone_code_is_just_code(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Zone full_path should be just the code."""
        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )
        assert zone.full_path == "Z01"

    def test_concatenates_ancestor_codes(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Full path should concatenate all ancestor codes with '-'."""
        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )
        aisle = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="aisle",
            code="A03",
            parent_location_id=zone.id,
        )

        assert aisle.full_path == "Z01-A03"

    def test_public_generate_location_code_method(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """The public generate_location_code method should work correctly."""
        zone = _create_location(
            db_session, org_id, warehouse_id, "zone", "Z01", full_path="Z01"
        )

        result = layout_service.generate_location_code(zone.id, "A01")
        assert result == "Z01-A01"

    def test_generate_code_with_no_parent(self, layout_service):
        """With no parent, code should be returned as-is."""
        result = layout_service.generate_location_code(None, "Z01")
        assert result == "Z01"


class TestDeactivateLocation:
    """Tests for deactivate_location method."""

    def test_deactivates_single_location(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Deactivating a leaf location should set is_active=False."""
        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )

        result = layout_service.deactivate_location(zone.id, org_id)
        assert result.is_active is False

    def test_cascades_to_descendants(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Deactivating a parent should cascade to all descendants."""
        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )
        aisle = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="aisle",
            code="A01",
            parent_location_id=zone.id,
        )
        bay = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="bay",
            code="B01",
            parent_location_id=aisle.id,
        )

        layout_service.deactivate_location(zone.id, org_id)

        # Refresh from DB
        db_session.refresh(aisle)
        db_session.refresh(bay)

        assert aisle.is_active is False
        assert bay.is_active is False

    def test_deactivate_nonexistent_raises_error(
        self, db_session, layout_service, org_id
    ):
        """Deactivating a non-existent location should raise ValidationError."""
        from app.core.exceptions import ValidationError

        with pytest.raises(ValidationError, match="not found"):
            layout_service.deactivate_location(uuid.uuid4(), org_id)


class TestUpdateLocation:
    """Tests for update_location method."""

    def test_update_name(self, db_session, layout_service, org_id, warehouse_id):
        """Should update the name field."""
        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
            name="Old Name",
        )

        updated = layout_service.update_location(zone.id, org_id, name="New Name")
        assert updated.name == "New Name"

    def test_update_capacity(self, db_session, layout_service, org_id, warehouse_id):
        """Should update the capacity field."""
        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )

        updated = layout_service.update_location(
            zone.id, org_id, capacity=Decimal("500")
        )
        assert updated.capacity == Decimal("500")

    def test_update_increments_version(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Each update should increment the version for optimistic locking."""
        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )
        original_version = zone.version

        updated = layout_service.update_location(zone.id, org_id, name="Updated")
        assert updated.version == original_version + 1


class TestGetTree:
    """Tests for get_tree method."""

    def test_returns_empty_for_no_locations(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Should return empty list when no locations exist."""
        tree = layout_service.get_tree(warehouse_id, org_id)
        assert tree == []

    def test_returns_nested_structure(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Should return a nested tree structure."""
        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )
        layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="aisle",
            code="A01",
            parent_location_id=zone.id,
        )

        tree = layout_service.get_tree(warehouse_id, org_id)

        assert len(tree) == 1
        assert tree[0]["code"] == "Z01"
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["code"] == "A01"


class TestListLocations:
    """Tests for list_locations method."""

    def test_filter_by_location_type(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Should filter locations by type."""
        layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )
        zone2 = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z02",
        )
        layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="aisle",
            code="A01",
            parent_location_id=zone2.id,
        )

        result = layout_service.list_locations(
            warehouse_id, org_id, location_type="zone"
        )

        assert result["pagination"]["total"] == 2
        assert len(result["locations"]) == 2
        assert all(loc.location_type == "zone" for loc in result["locations"])

    def test_pagination(self, db_session, layout_service, org_id, warehouse_id):
        """Should support pagination."""
        for i in range(5):
            layout_service.create_location(
                warehouse_id=warehouse_id,
                organization_id=org_id,
                location_type="zone",
                code=f"Z{i:02d}",
            )

        result = layout_service.list_locations(
            warehouse_id, org_id, page=1, page_size=2
        )

        assert result["pagination"]["total"] == 5
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["page_size"] == 2
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_prev"] is False
        assert len(result["locations"]) == 2

    def test_filter_by_is_active(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Should filter by active status."""
        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )
        layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z02",
        )
        layout_service.deactivate_location(zone.id, org_id)

        result = layout_service.list_locations(
            warehouse_id, org_id, is_active=True
        )
        assert result["pagination"]["total"] == 1
        assert result["locations"][0].code == "Z02"


class TestSearchLocations:
    """Tests for search_locations method."""

    def test_search_by_code(self, db_session, layout_service, org_id, warehouse_id):
        """Should find locations matching code."""
        layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
            name="Receiving",
        )
        layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z02",
            name="Storage",
        )

        results = layout_service.search_locations(warehouse_id, org_id, "Z01")
        assert len(results) == 1
        assert results[0].code == "Z01"

    def test_search_by_name(self, db_session, layout_service, org_id, warehouse_id):
        """Should find locations matching name."""
        layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
            name="Receiving Zone",
        )
        layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z02",
            name="Storage Zone",
        )

        results = layout_service.search_locations(warehouse_id, org_id, "Receiving")
        assert len(results) == 1
        assert results[0].name == "Receiving Zone"

    def test_search_case_insensitive(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Search should be case-insensitive."""
        layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
            name="Cold Storage",
        )

        results = layout_service.search_locations(warehouse_id, org_id, "cold")
        assert len(results) == 1


class TestGetLocationSummary:
    """Tests for get_location_summary method."""

    def test_summary_for_zone_with_bins(
        self, db_session, layout_service, org_id, warehouse_id
    ):
        """Should return correct summary stats for a zone subtree."""
        zone = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="zone",
            code="Z01",
        )
        aisle = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="aisle",
            code="A01",
            parent_location_id=zone.id,
        )
        bay = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="bay",
            code="B01",
            parent_location_id=aisle.id,
        )
        level = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="level",
            code="L01",
            parent_location_id=bay.id,
        )
        bin1 = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="bin",
            code="B01",
            parent_location_id=level.id,
            capacity=Decimal("100"),
        )
        bin2 = layout_service.create_location(
            warehouse_id=warehouse_id,
            organization_id=org_id,
            location_type="bin",
            code="B02",
            parent_location_id=level.id,
            capacity=Decimal("50"),
        )

        # Add stock to bin1
        item_id = uuid.uuid4()
        stock = BinStockLevel(
            id=uuid.uuid4(),
            organization_id=org_id,
            bin_location_id=bin1.id,
            item_id=item_id,
            quantity_on_hand=Decimal("30"),
            batch_number="BATCH-001",
        )
        db_session.add(stock)
        db_session.flush()

        summary = layout_service.get_location_summary(zone.id, org_id)

        assert summary["total_bins"] == 2
        assert summary["occupied_bins"] == 1
        assert summary["total_capacity"] == Decimal("150")
        assert summary["used_capacity"] == Decimal("30")
        assert summary["available_capacity"] == Decimal("120")
        assert summary["distinct_items"] == 1

    def test_summary_nonexistent_raises_error(
        self, db_session, layout_service, org_id
    ):
        """Should raise ValidationError for non-existent location."""
        from app.core.exceptions import ValidationError

        with pytest.raises(ValidationError, match="not found"):
            layout_service.get_location_summary(uuid.uuid4(), org_id)
