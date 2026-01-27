"""Supplier service with business logic"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateSupplierCodeException,
    SupplierNotFoundException,
)
from app.models.base import SupplierStatus
from app.models.supplier import Supplier
from app.repositories.supplier_repository import SupplierRepository
from app.schemas.supplier import SupplierCreate, SupplierUpdate


class SupplierService:
    """Service for supplier operations"""

    def __init__(self, db: Session):
        self.db = db
        self.supplier_repo = SupplierRepository(db)

    def create_supplier(
        self,
        supplier_data: SupplierCreate,
        organization_id: UUID,
        user_id: UUID,
    ) -> Supplier:
        """
        Create a new supplier.

        Args:
            supplier_data: Supplier creation data
            organization_id: Organization UUID
            user_id: User UUID creating the supplier

        Returns:
            Created Supplier object

        Raises:
            DuplicateSupplierCodeException: If supplier code already exists
        """
        if self.supplier_repo.supplier_code_exists(
            supplier_data.supplier_code, organization_id
        ):
            raise DuplicateSupplierCodeException(
                f"Supplier with code '{supplier_data.supplier_code}' already exists"
            )

        supplier_dict = supplier_data.model_dump()
        supplier_dict["organization_id"] = organization_id
        supplier_dict["created_by"] = user_id
        supplier_dict["updated_by"] = user_id

        if supplier_dict.get("status"):
            try:
                supplier_dict["status"] = SupplierStatus(
                    str(supplier_dict["status"]).lower()
                )
            except (ValueError, KeyError):
                supplier_dict["status"] = SupplierStatus.ACTIVE

        return self.supplier_repo.create_supplier(supplier_dict)

    def get_supplier_by_id(self, supplier_id: UUID, organization_id: UUID) -> Supplier:
        """
        Get supplier by ID.

        Args:
            supplier_id: Supplier UUID
            organization_id: Organization UUID

        Returns:
            Supplier object

        Raises:
            SupplierNotFoundException: If supplier not found
        """
        supplier = self.supplier_repo.get_supplier_by_id(
            supplier_id, organization_id
        )
        if not supplier:
            raise SupplierNotFoundException(
                f"Supplier with ID {supplier_id} not found"
            )
        return supplier

    def update_supplier(
        self,
        supplier_id: UUID,
        supplier_data: SupplierUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> Supplier:
        """
        Update a supplier.

        Args:
            supplier_id: Supplier UUID
            supplier_data: Supplier update data
            organization_id: Organization UUID
            user_id: User UUID updating the supplier

        Returns:
            Updated Supplier object

        Raises:
            SupplierNotFoundException: If supplier not found
        """
        supplier = self.supplier_repo.get_supplier_by_id(
            supplier_id, organization_id
        )
        if not supplier:
            raise SupplierNotFoundException(
                f"Supplier with ID {supplier_id} not found"
            )

        update_dict = supplier_data.model_dump(exclude_unset=True)
        update_dict["updated_by"] = user_id

        if "status" in update_dict and update_dict["status"]:
            try:
                update_dict["status"] = SupplierStatus(
                    str(update_dict["status"]).lower()
                )
            except (ValueError, KeyError):
                del update_dict["status"]

        return self.supplier_repo.update_supplier(supplier, update_dict)

    def delete_supplier(
        self,
        supplier_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> Supplier:
        """
        Soft delete a supplier.

        Args:
            supplier_id: Supplier UUID
            organization_id: Organization UUID
            user_id: User UUID deleting the supplier

        Returns:
            Deleted Supplier object

        Raises:
            SupplierNotFoundException: If supplier not found
        """
        supplier = self.supplier_repo.get_supplier_by_id(
            supplier_id, organization_id
        )
        if not supplier:
            raise SupplierNotFoundException(
                f"Supplier with ID {supplier_id} not found"
            )

        supplier.updated_by = user_id
        return self.supplier_repo.soft_delete_supplier(supplier)

    def get_suppliers(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Supplier], dict]:
        """
        Get paginated list of suppliers with filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by status (active, inactive, blocked)
            search: Search term
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of suppliers, pagination metadata)
        """
        page_size = min(page_size, 100)

        status_enum = None
        if status:
            try:
                status_enum = SupplierStatus(str(status).lower())
            except (ValueError, KeyError):
                pass

        suppliers, total_count = self.supplier_repo.list_suppliers(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            status=status_enum,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        total_pages = (total_count + page_size - 1) // page_size
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

        return suppliers, pagination
