"""Capacity service for computing and maintaining capacity rollups through the location hierarchy.

Handles:
- Recalculating ancestor capacities when a bin's capacity changes
- Computing available capacity (total_capacity minus stock in subtree)
- Providing capacity summaries for any location node
- Optimistic locking for concurrent updates
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StateError
from app.models.bin_stock_level import BinStockLevel
from app.models.warehouse_location import WarehouseLocation


class OptimisticLockError(StateError):
    """Raised when a concurrent update is detected via version mismatch."""

    def __init__(self, location_id: UUID):
        super().__init__(
            f"Concurrent update detected for location {location_id}. Please retry.",
            current_state="updating",
            required_state=["idle"],
        )


class CapacityService:
    """Service for computing and maintaining capacity rollups."""

    MAX_RETRIES = 3

    def __init__(self, db: Session):
        self.db = db

    def recalculate_ancestors(self, location_id: UUID) -> None:
        """Walk up the tree from the changed location to the root,
        recalculating total_capacity = sum(children capacities) at each level.

        For each ancestor:
        - total_capacity = sum of children's total_capacity (for non-leaf children)
                          or capacity (for leaf bins)
        - available_capacity = total_capacity - used capacity in subtree

        Uses optimistic locking with retry on conflict.

        Requirements: 2.1, 2.2, 2.3, 2.4, 2.6
        """
        location = (
            self.db.query(WarehouseLocation)
            .filter(WarehouseLocation.id == location_id)
            .first()
        )

        if not location:
            raise NotFoundError(
                f"Location with ID {location_id} not found",
                entity_type="WarehouseLocation",
                entity_id=str(location_id),
            )

        # Start from the parent of the changed location
        current_id = location.parent_location_id

        while current_id is not None:
            self._update_ancestor_capacity_with_retry(current_id)
            # Move to the next ancestor
            current = (
                self.db.query(WarehouseLocation)
                .filter(WarehouseLocation.id == current_id)
                .first()
            )
            if current is None:
                break
            current_id = current.parent_location_id

    def _update_ancestor_capacity_with_retry(self, location_id: UUID) -> None:
        """Update a single ancestor's capacity with optimistic locking and retry.

        Requirements: 18.5
        """
        for _attempt in range(self.MAX_RETRIES):
            location = (
                self.db.query(WarehouseLocation)
                .filter(WarehouseLocation.id == location_id)
                .first()
            )

            if location is None:
                return

            current_version = location.version or 1

            # Calculate total_capacity from active children
            # For children that are bins (leaf nodes), use their `capacity` field
            # For non-leaf children, use their `total_capacity` field
            # We use a unified approach: sum children's total_capacity,
            # but for bins (which have no children), total_capacity == capacity
            children_total = self.db.query(
                func.coalesce(func.sum(WarehouseLocation.total_capacity), Decimal("0"))
            ).filter(
                WarehouseLocation.parent_location_id == location_id,
                WarehouseLocation.is_active == True,  # noqa: E712
            ).scalar() or Decimal("0")

            # Compute used capacity in the subtree
            used = self._used_capacity_in_subtree(location_id)

            new_total = Decimal(str(children_total))
            new_available = new_total - used

            # Optimistic lock: update only if version hasn't changed
            rows_updated = (
                self.db.query(WarehouseLocation)
                .filter(
                    WarehouseLocation.id == location_id,
                    WarehouseLocation.version == current_version,
                )
                .update(
                    {
                        WarehouseLocation.total_capacity: new_total,
                        WarehouseLocation.available_capacity: new_available,
                        WarehouseLocation.version: current_version + 1,
                    },
                    synchronize_session="fetch",
                )
            )

            if rows_updated == 1:
                self.db.flush()
                return

            # Conflict detected — refresh and retry
            self.db.expire_all()

        # All retries exhausted
        raise OptimisticLockError(location_id)

    def compute_available_capacity(
        self, location_id: UUID, organization_id: UUID
    ) -> Decimal:
        """Compute available capacity for a location node.

        available_capacity = total_capacity - sum of stock quantities in subtree

        Requirements: 2.5
        """
        location = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id == location_id,
                WarehouseLocation.organization_id == organization_id,
            )
            .first()
        )

        if not location:
            raise NotFoundError(
                f"Location with ID {location_id} not found",
                entity_type="WarehouseLocation",
                entity_id=str(location_id),
            )

        total = Decimal(str(location.total_capacity or 0))
        used = self._used_capacity_in_subtree(location_id)

        return total - used

    def get_capacity_summary(self, location_id: UUID, organization_id: UUID) -> dict:
        """Get a capacity summary for any location node.

        Returns:
            dict with total_capacity, available_capacity, used_capacity,
            utilization_percentage, and child location counts.
        """
        location = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id == location_id,
                WarehouseLocation.organization_id == organization_id,
            )
            .first()
        )

        if not location:
            raise NotFoundError(
                f"Location with ID {location_id} not found",
                entity_type="WarehouseLocation",
                entity_id=str(location_id),
            )

        total_capacity = Decimal(str(location.total_capacity or 0))
        used_capacity = self._used_capacity_in_subtree(location_id)
        available_capacity = total_capacity - used_capacity

        # Calculate utilization percentage
        utilization_pct = Decimal("0")
        if total_capacity > 0:
            utilization_pct = (used_capacity / total_capacity) * Decimal("100")

        # Count children stats
        total_bins = self._count_bins_in_subtree(location_id)
        occupied_bins = self._count_occupied_bins_in_subtree(location_id)
        active_children = (
            self.db.query(func.count(WarehouseLocation.id))
            .filter(
                WarehouseLocation.parent_location_id == location_id,
                WarehouseLocation.is_active == True,  # noqa: E712
            )
            .scalar()
            or 0
        )

        return {
            "location_id": location_id,
            "location_type": location.location_type,
            "code": location.code,
            "full_path": location.full_path,
            "total_capacity": total_capacity,
            "available_capacity": available_capacity,
            "used_capacity": used_capacity,
            "utilization_percentage": round(utilization_pct, 2),
            "total_bins": total_bins,
            "occupied_bins": occupied_bins,
            "active_children": active_children,
            "version": location.version,
        }

    def update_location_capacity(
        self, location_id: UUID, new_capacity: Decimal
    ) -> None:
        """Update a leaf location's own capacity and trigger ancestor recalculation.

        This is called when a bin's capacity is set or updated.
        For leaf bins, total_capacity == capacity.

        Requirements: 2.1
        """
        location = (
            self.db.query(WarehouseLocation)
            .filter(WarehouseLocation.id == location_id)
            .first()
        )

        if not location:
            raise NotFoundError(
                f"Location with ID {location_id} not found",
                entity_type="WarehouseLocation",
                entity_id=str(location_id),
            )

        # Update the location's own capacity
        location.capacity = new_capacity
        # For leaf nodes (bins), total_capacity equals capacity
        location.total_capacity = new_capacity
        # Recalculate available for this node
        used = self._used_capacity_in_subtree(location_id)
        location.available_capacity = new_capacity - used
        location.version = (location.version or 1) + 1

        self.db.flush()

        # Recalculate all ancestors
        self.recalculate_ancestors(location_id)

    def _used_capacity_in_subtree(self, location_id: UUID) -> Decimal:
        """Calculate the total stock quantity stored in a location's subtree.

        For a bin (leaf node), this is the sum of bin_stock_levels.quantity_on_hand.
        For non-leaf nodes, this is the sum across all descendant bins.
        """
        # Get all descendant bin IDs (including self if it's a bin)
        bin_ids = self._get_descendant_bin_ids(location_id)

        if not bin_ids:
            # Check if the location itself is a bin
            location = (
                self.db.query(WarehouseLocation)
                .filter(WarehouseLocation.id == location_id)
                .first()
            )
            if location and location.location_type == "bin":
                bin_ids = [location_id]
            else:
                return Decimal("0")

        total_stock = self.db.query(
            func.coalesce(func.sum(BinStockLevel.quantity_on_hand), Decimal("0"))
        ).filter(BinStockLevel.bin_location_id.in_(bin_ids)).scalar() or Decimal("0")

        return Decimal(str(total_stock))

    def _get_descendant_bin_ids(self, location_id: UUID) -> list[UUID]:
        """Get all descendant bin location IDs for a given location using BFS."""
        bin_ids = []
        queue = [location_id]

        while queue:
            current_id = queue.pop(0)

            # Check if current is a bin
            current = (
                self.db.query(WarehouseLocation)
                .filter(
                    WarehouseLocation.id == current_id,
                    WarehouseLocation.is_active == True,  # noqa: E712
                )
                .first()
            )

            if current is None:
                continue

            if current.location_type == "bin":
                bin_ids.append(current.id)
            else:
                # Get children
                children_ids = (
                    self.db.query(WarehouseLocation.id)
                    .filter(
                        WarehouseLocation.parent_location_id == current_id,
                        WarehouseLocation.is_active == True,  # noqa: E712
                    )
                    .all()
                )
                queue.extend([c[0] for c in children_ids])

        return bin_ids

    def _count_bins_in_subtree(self, location_id: UUID) -> int:
        """Count total bins in the subtree of a location."""
        bin_ids = self._get_descendant_bin_ids(location_id)

        # Also check if the location itself is a bin
        location = (
            self.db.query(WarehouseLocation)
            .filter(WarehouseLocation.id == location_id)
            .first()
        )
        if location and location.location_type == "bin":
            if location_id not in bin_ids:
                bin_ids.append(location_id)

        return len(bin_ids)

    def _count_occupied_bins_in_subtree(self, location_id: UUID) -> int:
        """Count bins that have stock > 0 in the subtree."""
        bin_ids = self._get_descendant_bin_ids(location_id)

        # Also check if the location itself is a bin
        location = (
            self.db.query(WarehouseLocation)
            .filter(WarehouseLocation.id == location_id)
            .first()
        )
        if location and location.location_type == "bin":
            if location_id not in bin_ids:
                bin_ids.append(location_id)

        if not bin_ids:
            return 0

        occupied = (
            self.db.query(func.count(func.distinct(BinStockLevel.bin_location_id)))
            .filter(
                BinStockLevel.bin_location_id.in_(bin_ids),
                BinStockLevel.quantity_on_hand > 0,
            )
            .scalar()
            or 0
        )

        return occupied
