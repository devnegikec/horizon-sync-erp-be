"""Location allocation service for managing location-to-item-group allocations.

Manages exclusive and preferred allocations that control which items
go where during put-away operations.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.location_allocation import LocationAllocation
from app.models.warehouse_location import WarehouseLocation


class LocationAllocationService:
    """Service for managing location-to-item-group allocations."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create_allocation(
        self,
        location_id: UUID,
        item_group_id: UUID,
        organization_id: UUID,
        allocation_type: str = "preferred",
        priority: int = 0,
    ) -> LocationAllocation:
        """
        Create a location_allocation record linking a location to an item_group_id.

        Before creating an exclusive allocation, checks that no other active
        exclusive allocation exists for that location.

        Args:
            location_id: The location (bin, level, or bay) to allocate.
            item_group_id: The item group to allocate to this location.
            organization_id: Organization scope.
            allocation_type: 'exclusive' or 'preferred'.
            priority: Priority for put-away ordering (higher = more preferred).

        Returns:
            The created LocationAllocation.

        Raises:
            ValidationError: If validation fails (location not found, invalid type,
                or exclusive overlap detected).
        """
        # Validate allocation_type
        if allocation_type not in ("exclusive", "preferred"):
            raise ValidationError(
                f"Invalid allocation_type '{allocation_type}'. "
                "Must be 'exclusive' or 'preferred'."
            )

        # Validate location exists and belongs to the organization
        location = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id == location_id,
                WarehouseLocation.organization_id == organization_id,
            )
            .first()
        )
        if location is None:
            raise ValidationError(
                f"Location with ID '{location_id}' not found."
            )

        # Check exclusive overlap if creating an exclusive allocation
        if allocation_type == "exclusive":
            has_overlap = self.check_exclusive_overlap(
                location_id, item_group_id, organization_id
            )
            if has_overlap:
                raise ValidationError(
                    f"An active exclusive allocation already exists for location "
                    f"'{location.full_path or location_id}'. "
                    "A location cannot be exclusively allocated to multiple item groups."
                )

        allocation = LocationAllocation(
            organization_id=organization_id,
            location_id=location_id,
            item_group_id=item_group_id,
            allocation_type=allocation_type,
            priority=priority,
            is_active=True,
        )

        self.db.add(allocation)
        self.db.commit()
        self.db.refresh(allocation)
        return allocation

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update_allocation(
        self,
        allocation_id: UUID,
        organization_id: UUID,
        allocation_type: str | None = None,
        priority: int | None = None,
    ) -> LocationAllocation:
        """
        Update priority or allocation_type on an existing allocation.

        If changing to exclusive, validates no overlap exists.

        Args:
            allocation_id: The allocation to update.
            organization_id: Organization scope.
            allocation_type: New allocation type (optional).
            priority: New priority (optional).

        Returns:
            The updated LocationAllocation.

        Raises:
            ValidationError: If allocation not found or exclusive overlap detected.
        """
        allocation = self._get_allocation(allocation_id, organization_id)

        # Validate allocation_type if provided
        if allocation_type is not None:
            if allocation_type not in ("exclusive", "preferred"):
                raise ValidationError(
                    f"Invalid allocation_type '{allocation_type}'. "
                    "Must be 'exclusive' or 'preferred'."
                )

            # If changing to exclusive, check for overlap
            if (
                allocation_type == "exclusive"
                and allocation.allocation_type != "exclusive"
            ):
                has_overlap = self._check_exclusive_overlap_excluding(
                    allocation.location_id,
                    allocation.item_group_id,
                    organization_id,
                    exclude_allocation_id=allocation_id,
                )
                if has_overlap:
                    raise ValidationError(
                        "Cannot change to exclusive: an active exclusive allocation "
                        "already exists for this location."
                    )

            allocation.allocation_type = allocation_type

        if priority is not None:
            allocation.priority = priority

        allocation.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(allocation)
        return allocation

    # ------------------------------------------------------------------
    # DEACTIVATE
    # ------------------------------------------------------------------

    def deactivate_allocation(
        self,
        allocation_id: UUID,
        organization_id: UUID,
    ) -> LocationAllocation:
        """
        Set is_active=False on the allocation.

        Args:
            allocation_id: The allocation to deactivate.
            organization_id: Organization scope.

        Returns:
            The deactivated LocationAllocation.

        Raises:
            ValidationError: If allocation not found.
        """
        allocation = self._get_allocation(allocation_id, organization_id)

        allocation.is_active = False
        allocation.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(allocation)
        return allocation

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    def list_allocations(
        self,
        organization_id: UUID,
        warehouse_id: UUID | None = None,
        item_group_id: UUID | None = None,
        location_type: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """
        List allocations with filters and pagination.

        Args:
            organization_id: Organization scope.
            warehouse_id: Filter by warehouse (via location's warehouse_id).
            item_group_id: Filter by item group.
            location_type: Filter by location type (zone, aisle, bay, level, bin).
            is_active: Filter by active status.
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Dict with 'allocations' list and 'pagination' metadata.
        """
        query = self.db.query(LocationAllocation).filter(
            LocationAllocation.organization_id == organization_id,
        )

        if item_group_id is not None:
            query = query.filter(LocationAllocation.item_group_id == item_group_id)

        if is_active is not None:
            query = query.filter(LocationAllocation.is_active == is_active)

        # Filter by warehouse_id or location_type requires joining WarehouseLocation
        if warehouse_id is not None or location_type is not None:
            query = query.join(
                WarehouseLocation,
                LocationAllocation.location_id == WarehouseLocation.id,
            )
            if warehouse_id is not None:
                query = query.filter(
                    WarehouseLocation.warehouse_id == warehouse_id
                )
            if location_type is not None:
                query = query.filter(
                    WarehouseLocation.location_type == location_type
                )

        # Count total before pagination
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        allocations = (
            query.order_by(LocationAllocation.priority.desc(), LocationAllocation.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "allocations": allocations,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }

    # ------------------------------------------------------------------
    # CHECK EXCLUSIVE OVERLAP
    # ------------------------------------------------------------------

    def check_exclusive_overlap(
        self,
        location_id: UUID,
        item_group_id: UUID,
        organization_id: UUID,
    ) -> bool:
        """
        Return True if an active exclusive allocation already exists for the
        given location (regardless of item_group_id).

        This prevents overlapping exclusive allocations — the same location
        cannot be exclusively allocated to multiple item groups.

        Args:
            location_id: The location to check.
            item_group_id: The item group being allocated (not used in the check
                since we prevent ANY other exclusive allocation on the same location).
            organization_id: Organization scope.

        Returns:
            True if an active exclusive allocation exists for this location.
        """
        existing = (
            self.db.query(LocationAllocation)
            .filter(
                and_(
                    LocationAllocation.location_id == location_id,
                    LocationAllocation.organization_id == organization_id,
                    LocationAllocation.allocation_type == "exclusive",
                    LocationAllocation.is_active == True,  # noqa: E712
                )
            )
            .first()
        )
        return existing is not None

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _get_allocation(
        self,
        allocation_id: UUID,
        organization_id: UUID,
    ) -> LocationAllocation:
        """Get an allocation by ID, raising ValidationError if not found."""
        allocation = (
            self.db.query(LocationAllocation)
            .filter(
                LocationAllocation.id == allocation_id,
                LocationAllocation.organization_id == organization_id,
            )
            .first()
        )

        if allocation is None:
            raise ValidationError(
                f"Location allocation with ID '{allocation_id}' not found."
            )

        return allocation

    def _check_exclusive_overlap_excluding(
        self,
        location_id: UUID,
        item_group_id: UUID,
        organization_id: UUID,
        exclude_allocation_id: UUID,
    ) -> bool:
        """
        Check for exclusive overlap, excluding a specific allocation.

        Used during updates to avoid flagging the allocation being updated
        as an overlap with itself.
        """
        existing = (
            self.db.query(LocationAllocation)
            .filter(
                and_(
                    LocationAllocation.location_id == location_id,
                    LocationAllocation.organization_id == organization_id,
                    LocationAllocation.allocation_type == "exclusive",
                    LocationAllocation.is_active == True,  # noqa: E712
                    LocationAllocation.id != exclude_allocation_id,
                )
            )
            .first()
        )
        return existing is not None
