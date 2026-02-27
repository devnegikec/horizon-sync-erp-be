"""Exchange Rate repository for database operations"""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate


class ExchangeRateRepository:
    """Repository for Exchange Rate database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, rate_data: dict) -> ExchangeRate:
        """
        Create a new Exchange Rate record.

        Args:
            rate_data: Dictionary containing exchange rate data

        Returns:
            Created ExchangeRate object
        """
        exchange_rate = ExchangeRate(**rate_data)
        self.db.add(exchange_rate)
        self.db.commit()
        self.db.refresh(exchange_rate)
        return exchange_rate

    def get_by_id(self, rate_id: UUID, organization_id: UUID) -> ExchangeRate | None:
        """
        Get Exchange Rate by ID within an organization.

        Args:
            rate_id: ExchangeRate UUID
            organization_id: Organization UUID

        Returns:
            ExchangeRate object or None if not found
        """
        return (
            self.db.query(ExchangeRate)
            .filter(
                ExchangeRate.id == rate_id,
                ExchangeRate.organization_id == organization_id,
            )
            .first()
        )

    def get_by_currency_pair_and_date(
        self,
        organization_id: UUID,
        from_currency: str,
        to_currency: str,
        effective_date: date,
    ) -> ExchangeRate | None:
        """
        Get Exchange Rate by currency pair and effective date for upsert logic.

        Args:
            organization_id: Organization UUID
            from_currency: Source currency code
            to_currency: Target currency code
            effective_date: Effective date of the rate

        Returns:
            ExchangeRate object or None if not found
        """
        return (
            self.db.query(ExchangeRate)
            .filter(
                ExchangeRate.organization_id == organization_id,
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency,
                ExchangeRate.effective_date == effective_date,
            )
            .first()
        )

    def list(
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
    ) -> tuple[list[ExchangeRate], int]:
        """
        List Exchange Rates with pagination, org-scoped, filterable.

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
            Tuple of (list of ExchangeRate, total count)
        """
        query = self.db.query(ExchangeRate).filter(
            ExchangeRate.organization_id == organization_id,
        )

        if from_currency:
            query = query.filter(ExchangeRate.from_currency == from_currency)

        if to_currency:
            query = query.filter(ExchangeRate.to_currency == to_currency)

        if start_date:
            query = query.filter(ExchangeRate.effective_date >= start_date)

        if end_date:
            query = query.filter(ExchangeRate.effective_date <= end_date)

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        sort_column = getattr(ExchangeRate, sort_by, ExchangeRate.effective_date)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        exchange_rates = query.offset(offset).limit(page_size).all()

        return exchange_rates, total_count

    def update(self, exchange_rate: ExchangeRate, update_data: dict) -> ExchangeRate:
        """
        Update Exchange Rate fields.

        Args:
            exchange_rate: ExchangeRate object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated ExchangeRate object
        """
        for key, value in update_data.items():
            if hasattr(exchange_rate, key) and value is not None:
                setattr(exchange_rate, key, value)

        self.db.commit()
        self.db.refresh(exchange_rate)
        return exchange_rate

    def hard_delete(self, exchange_rate: ExchangeRate) -> None:
        """
        Hard delete an Exchange Rate record (permanently removes from database).

        Args:
            exchange_rate: ExchangeRate object to delete
        """
        self.db.delete(exchange_rate)
        self.db.commit()
