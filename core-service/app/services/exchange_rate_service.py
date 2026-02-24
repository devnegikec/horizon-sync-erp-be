"""Exchange Rate service with business logic"""

import logging
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ExchangeRateNotFoundException,
    ValidationException,
)
from app.models.exchange_rate import ExchangeRate
from app.repositories.exchange_rate_repository import ExchangeRateRepository
from app.schemas.exchange_rate import ExchangeRateCreate, ExchangeRateUpdate

logger = logging.getLogger(__name__)


class ExchangeRateService:
    """Service for Exchange Rate operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ExchangeRateRepository(db)

    def create_exchange_rate(
        self,
        rate_data: ExchangeRateCreate,
        organization_id: UUID,
    ) -> ExchangeRate:
        """
        Create a new Exchange Rate, or update existing if same org/pair/date exists (upsert).

        Args:
            rate_data: Exchange Rate creation data
            organization_id: Organization UUID

        Returns:
            Created or updated ExchangeRate object

        Raises:
            ValidationException: If from_currency equals to_currency
        """
        # Validate from_currency != to_currency
        if rate_data.from_currency == rate_data.to_currency:
            raise ValidationException(
                "from_currency and to_currency must be different"
            )

        # Default effective_date to today if not provided
        effective_date = rate_data.effective_date or date.today()

        # Upsert: check if same (org_id, from_currency, to_currency, effective_date) exists
        existing = self.repo.get_by_currency_pair_and_date(
            organization_id,
            rate_data.from_currency,
            rate_data.to_currency,
            effective_date,
        )
        if existing:
            # Update the existing record's rate and captured_at
            update_data = {
                "rate": rate_data.rate,
                "captured_at": datetime.now(UTC),
            }
            return self.repo.update(existing, update_data)

        # Create new record
        rate_dict = rate_data.model_dump()
        rate_dict["effective_date"] = effective_date
        rate_dict["organization_id"] = organization_id
        rate_dict["captured_at"] = datetime.now(UTC)

        return self.repo.create(rate_dict)

    def get_exchange_rate(
        self,
        rate_id: UUID,
        organization_id: UUID,
    ) -> ExchangeRate:
        """
        Get Exchange Rate by ID.

        Args:
            rate_id: ExchangeRate UUID
            organization_id: Organization UUID

        Returns:
            ExchangeRate object

        Raises:
            ExchangeRateNotFoundException: If exchange rate not found or belongs to different org
        """
        exchange_rate = self.repo.get_by_id(rate_id, organization_id)
        if not exchange_rate:
            raise ExchangeRateNotFoundException(
                f"Exchange rate with ID {rate_id} not found"
            )
        return exchange_rate

    def list_exchange_rates(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        from_currency: str | None = None,
        to_currency: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        sort_by: str = "effective_date",
        sort_order: str = "desc",
    ) -> tuple[list[ExchangeRate], dict]:
        """
        Get paginated list of Exchange Rates.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            from_currency: Optional filter by source currency
            to_currency: Optional filter by target currency
            start_date: Optional filter by start of effective date range
            end_date: Optional filter by end of effective date range
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of ExchangeRate, pagination metadata dict)
        """
        page_size = min(page_size, 100)

        exchange_rates, total_count = self.repo.list(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            from_currency=from_currency,
            to_currency=to_currency,
            start_date=start_date,
            end_date=end_date,
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

        return exchange_rates, pagination

    def update_exchange_rate(
        self,
        rate_id: UUID,
        rate_data: ExchangeRateUpdate,
        organization_id: UUID,
    ) -> ExchangeRate:
        """
        Update an Exchange Rate.

        Args:
            rate_id: ExchangeRate UUID
            rate_data: Exchange Rate update data
            organization_id: Organization UUID

        Returns:
            Updated ExchangeRate object

        Raises:
            ExchangeRateNotFoundException: If exchange rate not found
        """
        exchange_rate = self.repo.get_by_id(rate_id, organization_id)
        if not exchange_rate:
            raise ExchangeRateNotFoundException(
                f"Exchange rate with ID {rate_id} not found"
            )

        update_dict = rate_data.model_dump(exclude_unset=True)

        return self.repo.update(exchange_rate, update_dict)

    def delete_exchange_rate(
        self,
        rate_id: UUID,
        organization_id: UUID,
    ) -> None:
        """
        Hard delete an Exchange Rate.

        Args:
            rate_id: ExchangeRate UUID
            organization_id: Organization UUID

        Raises:
            ExchangeRateNotFoundException: If exchange rate not found
        """
        exchange_rate = self.repo.get_by_id(rate_id, organization_id)
        if not exchange_rate:
            raise ExchangeRateNotFoundException(
                f"Exchange rate with ID {rate_id} not found"
            )

        self.repo.hard_delete(exchange_rate)
