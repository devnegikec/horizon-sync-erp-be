"""Routing optimizer for warehouse bin traversal using nearest-neighbor heuristic with aisle grouping."""

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BinLocation:
    """Represents a bin location with position coordinates for routing optimization."""

    id: Any = None
    full_path: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    sort_order: int = 0
    extra: dict = field(default_factory=dict)


class RoutingOptimizer:
    """
    Calculates optimal traversal order for bin visits using nearest-neighbor
    heuristic with aisle grouping.

    Algorithm:
    1. Group locations by aisle (extracted from full_path)
    2. Sort aisle groups by distance from origin (using aisle centroid)
    3. Within each aisle, sort by nearest-neighbor starting from aisle entry point
    4. Assign sequential sort_order integers (1, 2, 3, ...)
    """

    @staticmethod
    def _extract_aisle(full_path: str) -> str:
        """
        Extract the aisle segment from a full_path.

        full_path format: Z01-A03-B02-L04-B01
        Aisle is the second segment (index 1), e.g., "A03".
        If the path has fewer than 2 segments, return the full path as the aisle.
        """
        if not full_path:
            return ""
        parts = full_path.split("-")
        if len(parts) >= 2:
            return parts[1]
        return parts[0]

    @staticmethod
    def _distance(point_a: tuple[float, float], point_b: tuple[float, float]) -> float:
        """Calculate Euclidean distance between two points."""
        dx = point_a[0] - point_b[0]
        dy = point_a[1] - point_b[1]
        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def _centroid(locations: list[BinLocation]) -> tuple[float, float]:
        """Calculate the centroid (average position) of a group of locations."""
        if not locations:
            return (0.0, 0.0)
        avg_x = sum(loc.position_x for loc in locations) / len(locations)
        avg_y = sum(loc.position_y for loc in locations) / len(locations)
        return (avg_x, avg_y)

    @classmethod
    def _nearest_neighbor_sort(
        cls, locations: list[BinLocation], start: tuple[float, float]
    ) -> list[BinLocation]:
        """
        Sort locations within an aisle using nearest-neighbor heuristic.

        Starting from the given start point, repeatedly pick the closest
        unvisited location.
        """
        if not locations:
            return []
        if len(locations) == 1:
            return list(locations)

        remaining = list(locations)
        sorted_locs: list[BinLocation] = []
        current_pos = start

        while remaining:
            # Find the nearest unvisited location
            nearest_idx = 0
            nearest_dist = cls._distance(
                current_pos, (remaining[0].position_x, remaining[0].position_y)
            )
            for i in range(1, len(remaining)):
                dist = cls._distance(
                    current_pos, (remaining[i].position_x, remaining[i].position_y)
                )
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = i

            nearest = remaining.pop(nearest_idx)
            sorted_locs.append(nearest)
            current_pos = (nearest.position_x, nearest.position_y)

        return sorted_locs

    def optimize(
        self,
        locations: list[BinLocation],
        origin: tuple[float, float] = (0.0, 0.0),
    ) -> list[BinLocation]:
        """
        Optimize the traversal order of bin locations.

        Args:
            locations: List of BinLocation objects with position_x, position_y, and full_path.
            origin: Starting point coordinates. Defaults to (0, 0).

        Returns:
            The same list of BinLocation objects with sort_order assigned (1-based).
        """
        if not locations:
            return []

        # Step 1: Group locations by aisle
        aisle_groups: dict[str, list[BinLocation]] = {}
        for loc in locations:
            aisle = self._extract_aisle(loc.full_path)
            if aisle not in aisle_groups:
                aisle_groups[aisle] = []
            aisle_groups[aisle].append(loc)

        # Step 2: Sort aisle groups by distance from origin (using centroid)
        aisle_order: list[tuple[str, list[BinLocation]]] = []
        remaining_aisles = list(aisle_groups.items())
        current_pos = origin

        # Use nearest-neighbor to order aisles themselves
        while remaining_aisles:
            nearest_idx = 0
            nearest_dist = self._distance(
                current_pos, self._centroid(remaining_aisles[0][1])
            )
            for i in range(1, len(remaining_aisles)):
                dist = self._distance(
                    current_pos, self._centroid(remaining_aisles[i][1])
                )
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = i

            aisle_name, aisle_locs = remaining_aisles.pop(nearest_idx)
            aisle_order.append((aisle_name, aisle_locs))
            # Move current position to the centroid of the selected aisle
            current_pos = self._centroid(aisle_locs)

        # Step 3: Within each aisle, sort by nearest-neighbor from the entry point
        result: list[BinLocation] = []
        entry_point = origin
        for _aisle_name, aisle_locs in aisle_order:
            sorted_in_aisle = self._nearest_neighbor_sort(aisle_locs, entry_point)
            result.extend(sorted_in_aisle)
            # Update entry point for next aisle to be the last location in this aisle
            if sorted_in_aisle:
                last = sorted_in_aisle[-1]
                entry_point = (last.position_x, last.position_y)

        # Step 4: Assign sequential sort_order integers (1-based)
        for i, loc in enumerate(result, start=1):
            loc.sort_order = i

        return result

    def optimize_dicts(
        self,
        locations: list[dict],
        origin: tuple[float, float] = (0.0, 0.0),
    ) -> list[dict]:
        """
        Convenience method that accepts and returns plain dicts.

        Each dict should have keys: full_path, position_x, position_y.
        Returns the same dicts with sort_order added/updated.
        """
        if not locations:
            return []

        # Convert dicts to BinLocation objects
        bin_locations = []
        for i, loc_dict in enumerate(locations):
            bin_loc = BinLocation(
                id=loc_dict.get("id", i),
                full_path=loc_dict.get("full_path", ""),
                position_x=float(loc_dict.get("position_x", 0)),
                position_y=float(loc_dict.get("position_y", 0)),
                extra=loc_dict,
            )
            bin_locations.append(bin_loc)

        # Optimize
        optimized = self.optimize(bin_locations, origin)

        # Update original dicts with sort_order
        result = []
        for bin_loc in optimized:
            loc_dict = bin_loc.extra
            loc_dict["sort_order"] = bin_loc.sort_order
            result.append(loc_dict)

        return result
