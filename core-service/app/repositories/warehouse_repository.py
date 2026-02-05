"""Warehouse repository for database operations"""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.base import WarehouseType
from app.models.warehouse import Warehouse


class WarehouseRepository:
    """Repository for warehouse database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_warehouse(self, warehouse_data: dict) -> Warehouse:
        """
        Create a new warehouse.

        Args:
            warehouse_data: Dictionary containing warehouse data

        Returns:
            Created Warehouse object
        """
        warehouse = Warehouse(**warehouse_data)
        self.db.add(warehouse)
        self.db.commit()
        self.db.refresh(warehouse)
        return warehouse

    def get_warehouse_by_id(
        self, warehouse_id: UUID, organization_id: UUID, include_parent: bool = False
    ) -> Warehouse | None:
        """
        Get warehouse by ID within an organization.

        Args:
            warehouse_id: Warehouse UUID
            organization_id: Organization UUID
            include_parent: Whether to include parent relationship

        Returns:
            Warehouse object or None if not found
        """
        query = self.db.query(Warehouse).filter(
            Warehouse.id == warehouse_id,
            Warehouse.organization_id == organization_id,
            Warehouse.deleted_at.is_(None),
        )

        if include_parent:
            query = query.options(joinedload(Warehouse.parent))

        return query.first()

    def get_warehouse_by_code(
        self, code: str, organization_id: UUID
    ) -> Warehouse | None:
        """
        Get warehouse by code within an organization.

        Args:
            code: Warehouse code
            organization_id: Organization UUID

        Returns:
            Warehouse object or None if not found
        """
        return (
            self.db.query(Warehouse)
            .filter(
                Warehouse.code == code,
                Warehouse.organization_id == organization_id,
                Warehouse.deleted_at.is_(None),
            )
            .first()
        )

    def update_warehouse(self, warehouse: Warehouse, update_data: dict) -> Warehouse:
        """
        Update warehouse fields.

        Args:
            warehouse: Warehouse object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated Warehouse object
        """
        for key, value in update_data.items():
            if hasattr(warehouse, key) and value is not None:
                setattr(warehouse, key, value)

        self.db.commit()
        self.db.refresh(warehouse)
        return warehouse

    def soft_delete_warehouse(self, warehouse: Warehouse) -> Warehouse:
        """
        Soft delete a warehouse.

        Args:
            warehouse: Warehouse object to delete

        Returns:
            Deleted Warehouse object
        """
        from datetime import UTC, datetime

        warehouse.deleted_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(warehouse)
        return warehouse

    def list_warehouses(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
        warehouse_type: WarehouseType | None = None,
        parent_warehouse_id: UUID | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Warehouse], int]:
        """
        List warehouses with pagination and filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            is_active: Filter by active status
            warehouse_type: Filter by warehouse type
            parent_warehouse_id: Filter by parent warehouse
            search: Search term for name, code
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of warehouses, total count)
        """
        query = self.db.query(Warehouse).filter(
            Warehouse.organization_id == organization_id,
            Warehouse.deleted_at.is_(None),
        )

        # Apply filters
        if is_active is not None:
            query = query.filter(Warehouse.is_active == is_active)

        if warehouse_type:
            query = query.filter(Warehouse.warehouse_type == warehouse_type)

        if parent_warehouse_id:
            query = query.filter(Warehouse.parent_warehouse_id == parent_warehouse_id)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Warehouse.name.ilike(search_term),
                    Warehouse.code.ilike(search_term),
                    Warehouse.city.ilike(search_term),
                )
            )

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        sort_column = getattr(Warehouse, sort_by, Warehouse.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        warehouses = query.offset(offset).limit(page_size).all()

        return warehouses, total_count

    def warehouse_code_exists(self, code: str, organization_id: UUID) -> bool:
        """
        Check if warehouse code already exists in the organization.

        Args:
            code: Warehouse code to check
            organization_id: Organization UUID

        Returns:
            True if code exists, False otherwise
        """
        return (
            self.db.query(Warehouse)
            .filter(
                Warehouse.code == code,
                Warehouse.organization_id == organization_id,
                Warehouse.deleted_at.is_(None),
            )
            .count()
            > 0
        )

    def get_all_warehouses(self, organization_id: UUID) -> list[Warehouse]:
        """
        Get all warehouses for an organization (for tree building).

        Args:
            organization_id: Organization UUID

        Returns:
            List of all warehouses
        """
        return (
            self.db.query(Warehouse)
            .filter(
                Warehouse.organization_id == organization_id,
                Warehouse.deleted_at.is_(None),
            )
            .order_by(Warehouse.name)
            .all()
        )

    def has_children(self, warehouse_id: UUID, organization_id: UUID) -> bool:
        """
        Check if warehouse has child warehouses.

        Args:
            warehouse_id: Warehouse UUID
            organization_id: Organization UUID

        Returns:
            True if has children, False otherwise
        """
        return (
            self.db.query(Warehouse)
            .filter(
                Warehouse.parent_warehouse_id == warehouse_id,
                Warehouse.organization_id == organization_id,
                Warehouse.deleted_at.is_(None),
            )
            .count()
            > 0
        )

    def set_default_warehouse(self, warehouse_id: UUID, organization_id: UUID) -> None:
        """
        Set a warehouse as default and unset others.

        Args:
            warehouse_id: Warehouse UUID to set as default
            organization_id: Organization UUID
        """
        # Unset all defaults
        self.db.query(Warehouse).filter(
            Warehouse.organization_id == organization_id,
            Warehouse.deleted_at.is_(None),
        ).update({"is_default": False})

        # Set the new default
        self.db.query(Warehouse).filter(
            Warehouse.id == warehouse_id,
            Warehouse.organization_id == organization_id,
        ).update({"is_default": True})

        self.db.commit()

    def get_warehouse_status_counts(self, organization_id: UUID) -> dict:
        """
        Get count of warehouses by status.

        Args:
            organization_id: Organization UUID

        Returns:
            Dictionary with status counts
        """
        from sqlalchemy import func

        # Get counts for active/inactive
        status_counts = (
            self.db.query(Warehouse.is_active, func.count(Warehouse.id))
            .filter(
                Warehouse.organization_id == organization_id,
                Warehouse.deleted_at.is_(None),
            )
            .group_by(Warehouse.is_active)
            .all()
        )

        # Initialize counts
        counts = {
            "active": 0,
            "inactive": 0,
            "total": 0,
        }

        # Populate counts from query results
        for is_active, count in status_counts:
            if is_active:
                counts["active"] = count
            else:
                counts["inactive"] = count
            counts["total"] += count

        return counts

    def get_warehouse_type_counts(self, organization_id: UUID) -> dict:
        """
        Get count of warehouses by type.

        Args:
            organization_id: Organization UUID

        Returns:
            Dictionary with type counts
        """
        from sqlalchemy import func

        # Get counts for each type
        type_counts = (
            self.db.query(Warehouse.warehouse_type, func.count(Warehouse.id))
            .filter(
                Warehouse.organization_id == organization_id,
                Warehouse.deleted_at.is_(None),
            )
            .group_by(Warehouse.warehouse_type)
            .all()
        )

        # Initialize counts
        counts = {
            "warehouse": 0,
            "store": 0,
            "virtual": 0,
            "transit": 0,
            "total": 0,
        }

        # Populate counts from query results
        for warehouse_type, count in type_counts:
            type_key = (
                warehouse_type.value
                if hasattr(warehouse_type, "value")
                else str(warehouse_type).lower()
            )
            if type_key in counts:
                counts[type_key] = count
            counts["total"] += count

        return counts
