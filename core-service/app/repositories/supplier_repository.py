"""Supplier repository for database operations"""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.base import SupplierStatus
from app.models.supplier import Supplier


class SupplierRepository:
    """Repository for supplier database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_supplier(self, supplier_data: dict) -> Supplier:
        """
        Create a new supplier.

        Args:
            supplier_data: Dictionary containing supplier data

        Returns:
            Created Supplier object
        """
        supplier = Supplier(**supplier_data)
        self.db.add(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    def get_supplier_by_id(
        self, supplier_id: UUID, organization_id: UUID
    ) -> Supplier | None:
        """
        Get supplier by ID within an organization.

        Args:
            supplier_id: Supplier UUID
            organization_id: Organization UUID

        Returns:
            Supplier object or None if not found
        """
        return (
            self.db.query(Supplier)
            .filter(
                Supplier.id == supplier_id,
                Supplier.organization_id == organization_id,
                Supplier.deleted_at.is_(None),
            )
            .first()
        )

    def get_supplier_by_code(
        self, supplier_code: str, organization_id: UUID
    ) -> Supplier | None:
        """
        Get supplier by code within an organization.

        Args:
            supplier_code: Supplier code
            organization_id: Organization UUID

        Returns:
            Supplier object or None if not found
        """
        return (
            self.db.query(Supplier)
            .filter(
                Supplier.supplier_code == supplier_code,
                Supplier.organization_id == organization_id,
                Supplier.deleted_at.is_(None),
            )
            .first()
        )

    def update_supplier(self, supplier: Supplier, update_data: dict) -> Supplier:
        """
        Update supplier fields.

        Args:
            supplier: Supplier object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated Supplier object
        """
        for key, value in update_data.items():
            if hasattr(supplier, key) and value is not None:
                setattr(supplier, key, value)

        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    def soft_delete_supplier(self, supplier: Supplier) -> Supplier:
        """
        Soft delete a supplier.

        Args:
            supplier: Supplier object to delete

        Returns:
            Deleted Supplier object
        """
        from datetime import UTC, datetime

        supplier.deleted_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    def list_suppliers(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: SupplierStatus | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Supplier], int]:
        """
        List suppliers with pagination and filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by status
            search: Search term for name, code, email
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of suppliers, total count)
        """
        query = self.db.query(Supplier).filter(
            Supplier.organization_id == organization_id,
            Supplier.deleted_at.is_(None),
        )

        if status is not None:
            query = query.filter(Supplier.status == status)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Supplier.supplier_name.ilike(search_term),
                    Supplier.supplier_code.ilike(search_term),
                    Supplier.email.ilike(search_term),
                    Supplier.city.ilike(search_term),
                )
            )

        total_count = query.count()

        sort_column = getattr(Supplier, sort_by, Supplier.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        offset = (page - 1) * page_size
        suppliers = query.offset(offset).limit(page_size).all()

        return suppliers, total_count

    def supplier_code_exists(self, supplier_code: str, organization_id: UUID) -> bool:
        """
        Check if supplier code already exists in the organization.

        Args:
            supplier_code: Supplier code to check
            organization_id: Organization UUID

        Returns:
            True if code exists, False otherwise
        """
        return (
            self.db.query(Supplier)
            .filter(
                Supplier.supplier_code == supplier_code,
                Supplier.organization_id == organization_id,
                Supplier.deleted_at.is_(None),
            )
            .count()
            > 0
        )
