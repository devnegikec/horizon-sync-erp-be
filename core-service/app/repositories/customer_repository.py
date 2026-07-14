"""Customer repository for database operations"""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.base import CustomerStatus
from app.models.customer import Customer


class CustomerRepository:
    """Repository for customer database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_customer(self, customer_data: dict) -> Customer:
        """
        Create a new customer.

        Args:
            customer_data: Dictionary containing customer data

        Returns:
            Created Customer object
        """
        customer = Customer(**customer_data)
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def get_customer_by_id(
        self, customer_id: UUID, organization_id: UUID
    ) -> Customer | None:
        """
        Get customer by ID within an organization.

        Args:
            customer_id: Customer UUID
            organization_id: Organization UUID

        Returns:
            Customer object or None if not found
        """
        return (
            self.db.query(Customer)
            .filter(
                Customer.id == customer_id,
                Customer.organization_id == organization_id,
                Customer.deleted_at.is_(None),
            )
            .first()
        )

    def get_customer_by_code(
        self, customer_code: str, organization_id: UUID
    ) -> Customer | None:
        """
        Get customer by code within an organization.

        Args:
            customer_code: Customer code
            organization_id: Organization UUID

        Returns:
            Customer object or None if not found
        """
        return (
            self.db.query(Customer)
            .filter(
                Customer.customer_code == customer_code,
                Customer.organization_id == organization_id,
                Customer.deleted_at.is_(None),
            )
            .first()
        )

    def update_customer(self, customer: Customer, update_data: dict) -> Customer:
        """
        Update customer fields.

        Args:
            customer: Customer object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated Customer object
        """
        for key, value in update_data.items():
            if hasattr(customer, key) and value is not None:
                setattr(customer, key, value)

        self.db.commit()
        self.db.refresh(customer)
        return customer

    def soft_delete_customer(self, customer: Customer) -> Customer:
        """
        Soft delete a customer.

        Args:
            customer: Customer object to delete

        Returns:
            Deleted Customer object
        """
        from datetime import UTC, datetime

        customer.deleted_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def list_customers(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: CustomerStatus | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Customer], int]:
        """
        List customers with pagination and filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by status
            search: Search term for name, code, email
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of customers, total count)
        """
        query = self.db.query(Customer).filter(
            Customer.organization_id == organization_id,
            Customer.deleted_at.is_(None),
        )

        if status is not None:
            query = query.filter(Customer.status == status)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Customer.customer_name.ilike(search_term),
                    Customer.customer_code.ilike(search_term),
                    Customer.email.ilike(search_term),
                    Customer.city.ilike(search_term),
                )
            )

        total_count = query.count()

        sort_column = getattr(Customer, sort_by, Customer.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        offset = (page - 1) * page_size
        customers = query.offset(offset).limit(page_size).all()

        return customers, total_count

    def customer_code_exists(self, customer_code: str, organization_id: UUID) -> bool:
        """
        Check if customer code already exists in the organization.

        Args:
            customer_code: Customer code to check
            organization_id: Organization UUID

        Returns:
            True if code exists, False otherwise
        """
        return (
            self.db.query(Customer)
            .filter(
                Customer.customer_code == customer_code,
                Customer.organization_id == organization_id,
                Customer.deleted_at.is_(None),
            )
            .count()
            > 0
        )

    def get_customer_status_counts(self, organization_id: UUID) -> dict:
        """
        Get count of customers by status.

        Args:
            organization_id: Organization UUID

        Returns:
            Dictionary with status counts
        """
        from sqlalchemy import func

        # Get counts for each status
        status_counts = (
            self.db.query(Customer.status, func.count(Customer.id))
            .filter(
                Customer.organization_id == organization_id,
                Customer.deleted_at.is_(None),
            )
            .group_by(Customer.status)
            .all()
        )

        # Initialize counts
        counts = {
            "active": 0,
            "inactive": 0,
            "blocked": 0,
            "total": 0,
        }

        # Populate counts from query results
        for status, count in status_counts:
            status_key = (
                status.value if hasattr(status, "value") else str(status).lower()
            )
            if status_key in counts:
                counts[status_key] = count
            counts["total"] += count

        return counts
