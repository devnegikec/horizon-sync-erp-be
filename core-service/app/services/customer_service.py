"""Customer service with business logic"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    CustomerNotFoundException,
    DuplicateCustomerCodeException,
)
from app.models.base import CustomerStatus
from app.models.customer import Customer
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerService:
    """Service for customer operations"""

    def __init__(self, db: Session):
        self.db = db
        self.customer_repo = CustomerRepository(db)

    def create_customer(
        self,
        customer_data: CustomerCreate,
        organization_id: UUID,
        user_id: UUID,
    ) -> Customer:
        """
        Create a new customer.

        Args:
            customer_data: Customer creation data
            organization_id: Organization UUID
            user_id: User UUID creating the customer

        Returns:
            Created Customer object

        Raises:
            DuplicateCustomerCodeException: If customer code already exists
        """
        if self.customer_repo.customer_code_exists(
            customer_data.customer_code, organization_id
        ):
            raise DuplicateCustomerCodeException(
                f"Customer with code '{customer_data.customer_code}' already exists"
            )

        customer_dict = customer_data.model_dump()
        customer_dict["organization_id"] = organization_id
        customer_dict["created_by"] = user_id
        customer_dict["updated_by"] = user_id

        if customer_dict.get("status"):
            try:
                customer_dict["status"] = CustomerStatus(
                    str(customer_dict["status"]).lower()
                )
            except (ValueError, KeyError):
                customer_dict["status"] = CustomerStatus.ACTIVE

        return self.customer_repo.create_customer(customer_dict)

    def get_customer_by_id(self, customer_id: UUID, organization_id: UUID) -> Customer:
        """
        Get customer by ID.

        Args:
            customer_id: Customer UUID
            organization_id: Organization UUID

        Returns:
            Customer object

        Raises:
            CustomerNotFoundException: If customer not found
        """
        customer = self.customer_repo.get_customer_by_id(
            customer_id, organization_id
        )
        if not customer:
            raise CustomerNotFoundException(
                f"Customer with ID {customer_id} not found"
            )
        return customer

    def update_customer(
        self,
        customer_id: UUID,
        customer_data: CustomerUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> Customer:
        """
        Update a customer.

        Args:
            customer_id: Customer UUID
            customer_data: Customer update data
            organization_id: Organization UUID
            user_id: User UUID updating the customer

        Returns:
            Updated Customer object

        Raises:
            CustomerNotFoundException: If customer not found
        """
        customer = self.customer_repo.get_customer_by_id(
            customer_id, organization_id
        )
        if not customer:
            raise CustomerNotFoundException(
                f"Customer with ID {customer_id} not found"
            )

        update_dict = customer_data.model_dump(exclude_unset=True)
        update_dict["updated_by"] = user_id

        if "status" in update_dict and update_dict["status"]:
            try:
                update_dict["status"] = CustomerStatus(
                    str(update_dict["status"]).lower()
                )
            except (ValueError, KeyError):
                del update_dict["status"]

        return self.customer_repo.update_customer(customer, update_dict)

    def delete_customer(
        self,
        customer_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> Customer:
        """
        Soft delete a customer.

        Args:
            customer_id: Customer UUID
            organization_id: Organization UUID
            user_id: User UUID deleting the customer

        Returns:
            Deleted Customer object

        Raises:
            CustomerNotFoundException: If customer not found
        """
        customer = self.customer_repo.get_customer_by_id(
            customer_id, organization_id
        )
        if not customer:
            raise CustomerNotFoundException(
                f"Customer with ID {customer_id} not found"
            )

        customer.updated_by = user_id
        return self.customer_repo.soft_delete_customer(customer)

    def get_customers(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Customer], dict]:
        """
        Get paginated list of customers with filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by status (active, inactive, blocked)
            search: Search term
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of customers, pagination metadata)
        """
        page_size = min(page_size, 100)

        status_enum = None
        if status:
            try:
                status_enum = CustomerStatus(str(status).lower())
            except (ValueError, KeyError):
                pass

        customers, total_count = self.customer_repo.list_customers(
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

        return customers, pagination
