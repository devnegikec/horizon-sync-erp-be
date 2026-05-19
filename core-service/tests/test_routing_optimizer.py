"""Unit tests for RoutingOptimizer service."""


import pytest

from app.services.routing_optimizer import BinLocation, RoutingOptimizer


@pytest.fixture
def optimizer():
    return RoutingOptimizer()


class TestExtractAisle:
    """Tests for aisle extraction from full_path."""

    def test_standard_path(self):
        """Extract aisle from a standard 5-segment path."""
        assert RoutingOptimizer._extract_aisle("Z01-A03-B02-L04-B01") == "A03"

    def test_three_segment_path(self):
        """Extract aisle from a 3-segment path."""
        assert RoutingOptimizer._extract_aisle("Z01-A01-B01") == "A01"

    def test_two_segment_path(self):
        """Extract aisle from a 2-segment path."""
        assert RoutingOptimizer._extract_aisle("Z01-A02") == "A02"

    def test_single_segment_path(self):
        """Single segment returns itself as the aisle."""
        assert RoutingOptimizer._extract_aisle("Z01") == "Z01"

    def test_empty_path(self):
        """Empty path returns empty string."""
        assert RoutingOptimizer._extract_aisle("") == ""


class TestDistance:
    """Tests for Euclidean distance calculation."""

    def test_same_point(self):
        assert RoutingOptimizer._distance((0, 0), (0, 0)) == 0.0

    def test_horizontal(self):
        assert RoutingOptimizer._distance((0, 0), (3, 0)) == 3.0

    def test_vertical(self):
        assert RoutingOptimizer._distance((0, 0), (0, 4)) == 4.0

    def test_diagonal(self):
        # 3-4-5 triangle
        assert RoutingOptimizer._distance((0, 0), (3, 4)) == 5.0


class TestCentroid:
    """Tests for centroid calculation."""

    def test_single_location(self):
        locs = [BinLocation(position_x=3.0, position_y=4.0)]
        assert RoutingOptimizer._centroid(locs) == (3.0, 4.0)

    def test_multiple_locations(self):
        locs = [
            BinLocation(position_x=0.0, position_y=0.0),
            BinLocation(position_x=4.0, position_y=6.0),
        ]
        assert RoutingOptimizer._centroid(locs) == (2.0, 3.0)

    def test_empty_list(self):
        assert RoutingOptimizer._centroid([]) == (0.0, 0.0)


class TestNearestNeighborSort:
    """Tests for nearest-neighbor sorting within an aisle."""

    def test_empty_list(self):
        result = RoutingOptimizer._nearest_neighbor_sort([], (0, 0))
        assert result == []

    def test_single_location(self):
        loc = BinLocation(position_x=5.0, position_y=5.0)
        result = RoutingOptimizer._nearest_neighbor_sort([loc], (0, 0))
        assert result == [loc]

    def test_picks_nearest_first(self):
        """Starting from origin, the nearest location should be first."""
        far = BinLocation(
            full_path="Z01-A01-B01-L01-B01", position_x=10.0, position_y=10.0
        )
        near = BinLocation(
            full_path="Z01-A01-B02-L01-B01", position_x=1.0, position_y=1.0
        )
        mid = BinLocation(
            full_path="Z01-A01-B03-L01-B01", position_x=5.0, position_y=5.0
        )

        result = RoutingOptimizer._nearest_neighbor_sort([far, near, mid], (0, 0))
        assert result[0] is near
        assert result[1] is mid
        assert result[2] is far


class TestOptimize:
    """Tests for the main optimize method."""

    def test_empty_list(self, optimizer):
        """Empty input returns empty output."""
        result = optimizer.optimize([])
        assert result == []

    def test_single_location(self, optimizer):
        """Single location gets sort_order 1."""
        loc = BinLocation(
            full_path="Z01-A01-B01-L01-B01", position_x=5.0, position_y=5.0
        )
        result = optimizer.optimize([loc])
        assert len(result) == 1
        assert result[0].sort_order == 1

    def test_sequential_sort_order(self, optimizer):
        """All locations get sequential sort_order starting from 1."""
        locations = [
            BinLocation(
                full_path="Z01-A01-B01-L01-B01", position_x=1.0, position_y=1.0
            ),
            BinLocation(
                full_path="Z01-A02-B01-L01-B01", position_x=5.0, position_y=5.0
            ),
            BinLocation(
                full_path="Z01-A03-B01-L01-B01", position_x=10.0, position_y=10.0
            ),
        ]
        result = optimizer.optimize(locations)
        sort_orders = [loc.sort_order for loc in result]
        assert sort_orders == [1, 2, 3]

    def test_aisle_grouping(self, optimizer):
        """Locations in the same aisle should be contiguous in the output."""
        locations = [
            BinLocation(
                full_path="Z01-A01-B01-L01-B01", position_x=1.0, position_y=1.0
            ),
            BinLocation(
                full_path="Z01-A02-B01-L01-B01", position_x=5.0, position_y=5.0
            ),
            BinLocation(
                full_path="Z01-A01-B02-L01-B01", position_x=2.0, position_y=2.0
            ),
            BinLocation(
                full_path="Z01-A02-B02-L01-B01", position_x=6.0, position_y=6.0
            ),
        ]
        result = optimizer.optimize(locations)

        # Extract aisles in order
        aisles_in_order = [
            RoutingOptimizer._extract_aisle(loc.full_path) for loc in result
        ]

        # Verify aisle grouping: same-aisle locations are contiguous
        seen_aisles = []
        for aisle in aisles_in_order:
            if not seen_aisles or seen_aisles[-1] != aisle:
                seen_aisles.append(aisle)

        # Each aisle should appear exactly once in the seen list
        assert len(seen_aisles) == 2
        assert set(seen_aisles) == {"A01", "A02"}

    def test_nearest_aisle_first(self, optimizer):
        """The aisle closest to origin should be visited first."""
        # A01 is at (1,1), A02 is at (10,10) — A01 should come first from origin (0,0)
        locations = [
            BinLocation(
                full_path="Z01-A02-B01-L01-B01", position_x=10.0, position_y=10.0
            ),
            BinLocation(
                full_path="Z01-A01-B01-L01-B01", position_x=1.0, position_y=1.0
            ),
        ]
        result = optimizer.optimize(locations, origin=(0.0, 0.0))
        assert RoutingOptimizer._extract_aisle(result[0].full_path) == "A01"
        assert RoutingOptimizer._extract_aisle(result[1].full_path) == "A02"

    def test_default_origin(self, optimizer):
        """Default origin is (0, 0)."""
        locations = [
            BinLocation(
                full_path="Z01-A01-B01-L01-B01", position_x=1.0, position_y=1.0
            ),
            BinLocation(
                full_path="Z01-A02-B01-L01-B01", position_x=10.0, position_y=10.0
            ),
        ]
        # Without specifying origin, should default to (0, 0)
        result = optimizer.optimize(locations)
        assert RoutingOptimizer._extract_aisle(result[0].full_path) == "A01"

    def test_custom_origin(self, optimizer):
        """Custom origin changes which aisle is visited first."""
        # With origin at (10, 10), A02 is closer
        locations = [
            BinLocation(
                full_path="Z01-A01-B01-L01-B01", position_x=1.0, position_y=1.0
            ),
            BinLocation(
                full_path="Z01-A02-B01-L01-B01", position_x=9.0, position_y=9.0
            ),
        ]
        result = optimizer.optimize(locations, origin=(10.0, 10.0))
        assert RoutingOptimizer._extract_aisle(result[0].full_path) == "A02"
        assert RoutingOptimizer._extract_aisle(result[1].full_path) == "A01"

    def test_preserves_all_locations(self, optimizer):
        """Output contains exactly the same locations as input (no loss or duplication)."""
        locations = [
            BinLocation(
                id=1, full_path="Z01-A01-B01-L01-B01", position_x=1.0, position_y=1.0
            ),
            BinLocation(
                id=2, full_path="Z01-A02-B01-L01-B01", position_x=5.0, position_y=5.0
            ),
            BinLocation(
                id=3, full_path="Z01-A01-B02-L01-B01", position_x=2.0, position_y=2.0
            ),
            BinLocation(
                id=4, full_path="Z01-A03-B01-L01-B01", position_x=8.0, position_y=8.0
            ),
        ]
        result = optimizer.optimize(locations)
        result_ids = {loc.id for loc in result}
        assert result_ids == {1, 2, 3, 4}
        assert len(result) == 4

    def test_multiple_bins_same_aisle_nearest_neighbor(self, optimizer):
        """Within an aisle, bins are sorted by nearest-neighbor from entry point."""
        locations = [
            BinLocation(
                full_path="Z01-A01-B03-L01-B01", position_x=3.0, position_y=0.0
            ),
            BinLocation(
                full_path="Z01-A01-B01-L01-B01", position_x=1.0, position_y=0.0
            ),
            BinLocation(
                full_path="Z01-A01-B02-L01-B01", position_x=2.0, position_y=0.0
            ),
        ]
        result = optimizer.optimize(locations, origin=(0.0, 0.0))
        # From origin (0,0), nearest is B01 at (1,0), then B02 at (2,0), then B03 at (3,0)
        positions = [(loc.position_x, loc.position_y) for loc in result]
        assert positions == [(1.0, 0.0), (2.0, 0.0), (3.0, 0.0)]

    def test_three_aisles_ordering(self, optimizer):
        """Three aisles are visited in nearest-neighbor order from origin."""
        locations = [
            # Aisle A03 - far from origin
            BinLocation(
                full_path="Z01-A03-B01-L01-B01", position_x=20.0, position_y=20.0
            ),
            # Aisle A01 - close to origin
            BinLocation(
                full_path="Z01-A01-B01-L01-B01", position_x=2.0, position_y=2.0
            ),
            # Aisle A02 - medium distance
            BinLocation(
                full_path="Z01-A02-B01-L01-B01", position_x=10.0, position_y=10.0
            ),
        ]
        result = optimizer.optimize(locations, origin=(0.0, 0.0))
        aisles = [RoutingOptimizer._extract_aisle(loc.full_path) for loc in result]
        assert aisles == ["A01", "A02", "A03"]


class TestOptimizeDicts:
    """Tests for the dict-based convenience method."""

    def test_empty_list(self, optimizer):
        assert optimizer.optimize_dicts([]) == []

    def test_basic_dict_optimization(self, optimizer):
        """Dict-based method works with standard dict input."""
        locations = [
            {
                "id": "loc1",
                "full_path": "Z01-A02-B01-L01-B01",
                "position_x": 10,
                "position_y": 10,
            },
            {
                "id": "loc2",
                "full_path": "Z01-A01-B01-L01-B01",
                "position_x": 1,
                "position_y": 1,
            },
        ]
        result = optimizer.optimize_dicts(locations, origin=(0.0, 0.0))
        assert len(result) == 2
        # A01 should come first (closer to origin)
        assert result[0]["id"] == "loc2"
        assert result[0]["sort_order"] == 1
        assert result[1]["id"] == "loc1"
        assert result[1]["sort_order"] == 2

    def test_sort_order_assigned_to_dicts(self, optimizer):
        """sort_order is added to each dict."""
        locations = [
            {"full_path": "Z01-A01-B01-L01-B01", "position_x": 1, "position_y": 1},
            {"full_path": "Z01-A01-B02-L01-B01", "position_x": 2, "position_y": 2},
            {"full_path": "Z01-A01-B03-L01-B01", "position_x": 3, "position_y": 3},
        ]
        result = optimizer.optimize_dicts(locations)
        sort_orders = [d["sort_order"] for d in result]
        assert sort_orders == [1, 2, 3]

    def test_handles_missing_fields(self, optimizer):
        """Dicts with missing position fields default to 0."""
        locations = [
            {"full_path": "Z01-A01-B01-L01-B01"},
            {"full_path": "Z01-A01-B02-L01-B01", "position_x": 5},
        ]
        result = optimizer.optimize_dicts(locations)
        assert len(result) == 2
        assert all("sort_order" in d for d in result)
