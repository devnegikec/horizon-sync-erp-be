"""Location repository for warehouse location hierarchy database operations"""

from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from app.models.warehouse_location import WarehouseLocation


class LocationRepository:
    """Repository for warehouse location CRUD and hierarchy queries."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create(self, data: dict) -> WarehouseLocation:
        """
        Create a new warehouse location.

        Args:
            data: Dictionary containing location fields.

        Returns:
            Created WarehouseLocation object.
        """
        location = WarehouseLocation(**data)
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)
        return location

    # ------------------------------------------------------------------
    # GET BY ID
    # ------------------------------------------------------------------

    def get_by_id(
        self, location_id: UUID, org_id: UUID
    ) -> WarehouseLocation | None:
        """
        Get a single location by ID scoped to an organization.

        Args:
            location_id: The location UUID.
            org_id: Organization UUID for tenant isolation.

        Returns:
            WarehouseLocation or None if not found.
        """
        return (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id == location_id,
                WarehouseLocation.organization_id == org_id,
            )
            .first()
        )

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(
        self, location_id: UUID, data: dict
    ) -> WarehouseLocation | None:
        """
        Update location fields by ID.

        Args:
            location_id: The location UUID.
            data: Dictionary of fields to update.

        Returns:
            Updated WarehouseLocation or None if not found.
        """
        location = (
            self.db.query(WarehouseLocation)
            .filter(WarehouseLocation.id == location_id)
            .first()
        )
        if location is None:
            return None

        for key, value in data.items():
            if hasattr(location, key) and value is not None:
                setattr(location, key, value)

        self.db.commit()
        self.db.refresh(location)
        return location

    # ------------------------------------------------------------------
    # GET TREE (recursive CTE)
    # ------------------------------------------------------------------

    def get_tree(
        self, warehouse_id: UUID, org_id: UUID
    ) -> list[WarehouseLocation]:
        """
        Get the full location hierarchy for a warehouse using a recursive CTE.

        The CTE starts from root locations (zones with no parent) and
        recursively joins children. Results are ordered by full_path for
        deterministic tree construction.

        Args:
            warehouse_id: The warehouse UUID.
            org_id: Organization UUID for tenant isolation.

        Returns:
            List of WarehouseLocation objects ordered for tree building.
        """
        # Use a recursive CTE to fetch the entire hierarchy in one query
        cte = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
                WarehouseLocation.parent_location_id.is_(None),
            )
            .cte(name="location_tree", recursive=True)
        )

        # Recursive part: join children to the CTE
        cte_alias = cte.alias("lt")
        recursive_part = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.parent_location_id == cte_alias.c.id,
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
            )
        )

        cte = cte.union_all(recursive_part)

        # Query the CTE and order by full_path for tree construction
        locations = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id.in_(
                    self.db.query(cte.c.id)
                )
            )
            .order_by(WarehouseLocation.full_path)
            .all()
        )

        return locations

    # ------------------------------------------------------------------
    # LIST LOCATIONS (filtered + paginated)
    # ------------------------------------------------------------------

    def list_locations(
        self,
        org_id: UUID,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[WarehouseLocation], int]:
        """
        List locations with optional filters and pagination.

        Args:
            org_id: Organization UUID for tenant isolation.
            filters: Optional dict with keys:
                - warehouse_id: UUID
                - location_type: str (zone, aisle, bay, level, bin)
                - parent_location_id: UUID
                - is_active: bool
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Tuple of (list of locations, total count).
        """
        query = self.db.query(WarehouseLocation).filter(
            WarehouseLocation.organization_id == org_id,
        )

        if filters:
            if filters.get("warehouse_id"):
                query = query.filter(
                    WarehouseLocation.warehouse_id == filters["warehouse_id"]
                )
            if filters.get("location_type"):
                query = query.filter(
                    WarehouseLocation.location_type == filters["location_type"]
                )
            if filters.get("parent_location_id"):
                query = query.filter(
                    WarehouseLocation.parent_location_id
                    == filters["parent_location_id"]
                )
            if "is_active" in filters and filters["is_active"] is not None:
                query = query.filter(
                    WarehouseLocation.is_active == filters["is_active"]
                )

        # Total count before pagination
        total = query.count()

        # Apply ordering and pagination
        offset = (page - 1) * page_size
        locations = (
            query.order_by(WarehouseLocation.full_path)
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return locations, total

    # ------------------------------------------------------------------
    # GET CHILDREN (direct children of a location)
    # ------------------------------------------------------------------

    def get_children(
        self, parent_id: UUID, org_id: UUID
    ) -> list[WarehouseLocation]:
        """
        Get direct children of a location.

        Args:
            parent_id: The parent location UUID.
            org_id: Organization UUID for tenant isolation.

        Returns:
            List of direct child WarehouseLocation objects.
        """
        return (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.parent_location_id == parent_id,
                WarehouseLocation.organization_id == org_id,
            )
            .order_by(WarehouseLocation.full_path)
            .all()
        )

    # ------------------------------------------------------------------
    # GET DESCENDANTS (recursive - all descendants)
    # ------------------------------------------------------------------

    def get_descendants(
        self, location_id: UUID, org_id: UUID
    ) -> list[WarehouseLocation]:
        """
        Get all descendants of a location using a recursive CTE.

        Args:
            location_id: The root location UUID.
            org_id: Organization UUID for tenant isolation.

        Returns:
            List of all descendant WarehouseLocation objects.
        """
        # Anchor: direct children of the given location
        cte = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.parent_location_id == location_id,
                WarehouseLocation.organization_id == org_id,
            )
            .cte(name="descendants", recursive=True)
        )

        # Recursive part: children of the current level
        cte_alias = cte.alias("d")
        recursive_part = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.parent_location_id == cte_alias.c.id,
                WarehouseLocation.organization_id == org_id,
            )
        )

        cte = cte.union_all(recursive_part)

        # Query the CTE
        descendants = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id.in_(
                    self.db.query(cte.c.id)
                )
            )
            .order_by(WarehouseLocation.full_path)
            .all()
        )

        return descendants

    # ------------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------------

    def search(
        self,
        warehouse_id: UUID,
        org_id: UUID,
        query: str,
        limit: int = 20,
    ) -> list[WarehouseLocation]:
        """
        Search locations by code, full_path, or name (case-insensitive).

        Args:
            warehouse_id: The warehouse UUID to scope the search.
            org_id: Organization UUID for tenant isolation.
            query: Search string to match against code, full_path, or name.
            limit: Maximum results to return.

        Returns:
            List of matching WarehouseLocation objects.
        """
        search_pattern = f"%{query}%"

        return (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.organization_id == org_id,
                or_(
                    WarehouseLocation.code.ilike(search_pattern),
                    WarehouseLocation.full_path.ilike(search_pattern),
                    WarehouseLocation.name.ilike(search_pattern),
                ),
            )
            .order_by(WarehouseLocation.full_path)
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------
    # DEACTIVATE SUBTREE
    # ------------------------------------------------------------------

    def deactivate_subtree(self, location_id: UUID) -> int:
        """
        Deactivate a location and all its descendants.

        Uses a recursive CTE to find all descendant IDs, then performs
        a bulk update setting is_active=False and incrementing version.

        Args:
            location_id: The root location UUID to deactivate.

        Returns:
            Number of locations deactivated (including the root).
        """
        # Build the set of IDs to deactivate: the location itself + all descendants
        # Anchor: the location itself
        cte = (
            self.db.query(WarehouseLocation.id)
            .filter(WarehouseLocation.id == location_id)
            .cte(name="subtree", recursive=True)
        )

        # Recursive part: children
        cte_alias = cte.alias("st")
        recursive_part = (
            self.db.query(WarehouseLocation.id)
            .filter(WarehouseLocation.parent_location_id == cte_alias.c.id)
        )

        cte = cte.union_all(recursive_part)

        # Bulk update all locations in the subtree
        subtree_ids = self.db.query(cte.c.id).all()
        id_list = [row[0] for row in subtree_ids]

        if not id_list:
            return 0

        updated = (
            self.db.query(WarehouseLocation)
            .filter(WarehouseLocation.id.in_(id_list))
            .update(
                {
                    WarehouseLocation.is_active: False,
                    WarehouseLocation.version: WarehouseLocation.version + 1,
                },
                synchronize_session="fetch",
            )
        )

        self.db.commit()
        return updated
