"""Currency Master service with business logic"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    CurrencyNotFoundException,
    DuplicateCurrencyCodeException,
)
from app.models.currency_master import CurrencyMaster
from app.repositories.currency_master_repository import CurrencyMasterRepository
from app.schemas.currency_master import CurrencyMasterCreate, CurrencyMasterUpdate

logger = logging.getLogger(__name__)


class CurrencyMasterService:
    """Service for Currency Master operations"""

    def __init__(self, db: Session):
        self.db = db
        self.currency_repo = CurrencyMasterRepository(db)

    def create_currency(
        self,
        currency_data: CurrencyMasterCreate,
        organization_id: UUID,
        user_id: UUID,
    ) -> CurrencyMaster:
        """
        Create a new Currency.

        Args:
            currency_data: Currency creation data
            organization_id: Organization UUID
            user_id: User UUID creating the currency

        Returns:
            Created CurrencyMaster object

        Raises:
            DuplicateCurrencyCodeException: If currency code already exists in org
        """
        # Check duplicate code within org
        existing = self.currency_repo.get_by_code(currency_data.code, organization_id)
        if existing:
            raise DuplicateCurrencyCodeException(
                f"Currency with code '{currency_data.code}' already exists in this organization"
            )

        # Enforce base currency toggle: clear others before creating
        if currency_data.is_base_currency:
            self.currency_repo.clear_base_currency(organization_id)

        # Prepare data and delegate to repository
        currency_dict = currency_data.model_dump()
        currency_dict["organization_id"] = organization_id
        currency_dict["created_by"] = user_id
        currency_dict["updated_by"] = user_id

        return self.currency_repo.create(currency_dict)

    def get_currency(
        self,
        currency_id: UUID,
        organization_id: UUID,
    ) -> CurrencyMaster:
        """
        Get Currency by ID.

        Args:
            currency_id: Currency UUID
            organization_id: Organization UUID

        Returns:
            CurrencyMaster object

        Raises:
            CurrencyNotFoundException: If currency not found or belongs to different org
        """
        currency = self.currency_repo.get_by_id(currency_id, organization_id)
        if not currency:
            raise CurrencyNotFoundException(f"Currency with ID {currency_id} not found")
        return currency

    def list_currencies(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[CurrencyMaster], dict]:
        """
        Get paginated list of Currencies.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            search: Optional search term for code or name
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of CurrencyMaster, pagination metadata dict)
        """
        page_size = min(page_size, 100)

        currencies, total_count = self.currency_repo.list(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        total_pages = (total_count + page_size - 1) // page_size if page_size else 0
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

        return currencies, pagination

    def update_currency(
        self,
        currency_id: UUID,
        currency_data: CurrencyMasterUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> CurrencyMaster:
        """
        Update a Currency.

        Args:
            currency_id: Currency UUID
            currency_data: Currency update data
            organization_id: Organization UUID
            user_id: User UUID updating the currency

        Returns:
            Updated CurrencyMaster object

        Raises:
            CurrencyNotFoundException: If currency not found
        """
        currency = self.currency_repo.get_by_id(currency_id, organization_id)
        if not currency:
            raise CurrencyNotFoundException(f"Currency with ID {currency_id} not found")

        update_dict = currency_data.model_dump(exclude_unset=True)

        # Enforce base currency toggle on update
        if update_dict.get("is_base_currency") is True:
            self.currency_repo.clear_base_currency(organization_id)

        update_dict["updated_by"] = user_id

        return self.currency_repo.update(currency, update_dict)

    def delete_currency(
        self,
        currency_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> CurrencyMaster:
        """
        Soft delete a Currency.

        Args:
            currency_id: Currency UUID
            organization_id: Organization UUID
            user_id: User UUID deleting the currency

        Returns:
            Soft-deleted CurrencyMaster object

        Raises:
            CurrencyNotFoundException: If currency not found
        """
        currency = self.currency_repo.get_by_id(currency_id, organization_id)
        if not currency:
            raise CurrencyNotFoundException(f"Currency with ID {currency_id} not found")

        currency.updated_by = user_id
        return self.currency_repo.soft_delete(currency)
