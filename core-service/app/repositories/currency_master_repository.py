"""Currency Master repository for database operations"""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.currency_master import CurrencyMaster


class CurrencyMasterRepository:
    """Repository for Currency Master database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, currency_data: dict) -> CurrencyMaster:
        """
        Create a new Currency Master record.

        Args:
            currency_data: Dictionary containing currency data

        Returns:
            Created CurrencyMaster object
        """
        currency = CurrencyMaster(**currency_data)
        self.db.add(currency)
        self.db.commit()
        self.db.refresh(currency)
        return currency

    def get_by_id(
        self, currency_id: UUID, organization_id: UUID
    ) -> CurrencyMaster | None:
        """
        Get Currency by ID within an organization, excluding soft-deleted.

        Args:
            currency_id: Currency UUID
            organization_id: Organization UUID

        Returns:
            CurrencyMaster object or None if not found
        """
        return (
            self.db.query(CurrencyMaster)
            .filter(
                CurrencyMaster.id == currency_id,
                CurrencyMaster.organization_id == organization_id,
                CurrencyMaster.deleted_at.is_(None),
            )
            .first()
        )

    def get_by_code(self, code: str, organization_id: UUID) -> CurrencyMaster | None:
        """
        Get Currency by code within an organization for uniqueness checks.

        Args:
            code: ISO 4217 currency code (3 uppercase letters)
            organization_id: Organization UUID

        Returns:
            CurrencyMaster object or None if not found
        """
        return (
            self.db.query(CurrencyMaster)
            .filter(
                CurrencyMaster.code == code,
                CurrencyMaster.organization_id == organization_id,
                CurrencyMaster.deleted_at.is_(None),
            )
            .first()
        )

    def clear_base_currency(self, organization_id: UUID) -> None:
        """
        Set is_base_currency = false on all currencies in an organization.

        Used before setting a new base currency to enforce the single base currency invariant.

        Args:
            organization_id: Organization UUID
        """
        self.db.query(CurrencyMaster).filter(
            CurrencyMaster.organization_id == organization_id,
            CurrencyMaster.is_base_currency.is_(True),
            CurrencyMaster.deleted_at.is_(None),
        ).update({"is_base_currency": False})
        self.db.commit()

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[CurrencyMaster], int]:
        """
        List currencies with pagination, org-scoped, excluding soft-deleted.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            search: Optional search term for code or name
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of CurrencyMaster, total count)
        """
        query = self.db.query(CurrencyMaster).filter(
            CurrencyMaster.organization_id == organization_id,
            CurrencyMaster.deleted_at.is_(None),
        )

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    CurrencyMaster.code.ilike(search_term),
                    CurrencyMaster.name.ilike(search_term),
                )
            )

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        sort_column = getattr(CurrencyMaster, sort_by, CurrencyMaster.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        currencies = query.offset(offset).limit(page_size).all()

        return currencies, total_count

    def update(self, currency: CurrencyMaster, update_data: dict) -> CurrencyMaster:
        """
        Update Currency Master fields.

        Args:
            currency: CurrencyMaster object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated CurrencyMaster object
        """
        for key, value in update_data.items():
            if hasattr(currency, key) and value is not None:
                setattr(currency, key, value)

        self.db.commit()
        self.db.refresh(currency)
        return currency

    def soft_delete(self, currency: CurrencyMaster) -> CurrencyMaster:
        """
        Soft delete a Currency by setting deleted_at.

        Args:
            currency: CurrencyMaster object to delete

        Returns:
            Soft-deleted CurrencyMaster object
        """
        from datetime import UTC, datetime

        currency.deleted_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(currency)
        return currency
