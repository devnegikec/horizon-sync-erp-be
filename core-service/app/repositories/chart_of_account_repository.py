"""Chart of Account repository for database operations"""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.base import AccountType
from app.models.chart_of_account import ChartOfAccount


class ChartOfAccountRepository:
    """Repository for chart of account database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_chart_of_account(self, data: dict) -> ChartOfAccount:
        """
        Create a new chart of account.

        Args:
            data: Dictionary containing chart of account data

        Returns:
            Created ChartOfAccount object
        """
        account = ChartOfAccount(**data)
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def get_by_id(
        self,
        account_id: UUID,
        organization_id: UUID,
        include_parent: bool = False,
    ) -> ChartOfAccount | None:
        """
        Get chart of account by ID within an organization.

        Args:
            account_id: Chart of account UUID
            organization_id: Organization UUID
            include_parent: Whether to include parent relationship

        Returns:
            ChartOfAccount object or None if not found
        """
        query = self.db.query(ChartOfAccount).filter(
            ChartOfAccount.id == account_id,
            ChartOfAccount.organization_id == organization_id,
            ChartOfAccount.deleted_at.is_(None),
        )

        if include_parent:
            query = query.options(joinedload(ChartOfAccount.parent))

        return query.first()

    def get_by_code(
        self, account_code: str, organization_id: UUID
    ) -> ChartOfAccount | None:
        """
        Get chart of account by code within an organization.

        Args:
            account_code: Account code
            organization_id: Organization UUID

        Returns:
            ChartOfAccount object or None if not found
        """
        return (
            self.db.query(ChartOfAccount)
            .filter(
                ChartOfAccount.account_code == account_code,
                ChartOfAccount.organization_id == organization_id,
                ChartOfAccount.deleted_at.is_(None),
            )
            .first()
        )

    def update(self, account: ChartOfAccount, update_data: dict) -> ChartOfAccount:
        """
        Update chart of account fields.

        Args:
            account: ChartOfAccount object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated ChartOfAccount object
        """
        for key, value in update_data.items():
            if hasattr(account, key) and value is not None:
                setattr(account, key, value)

        self.db.commit()
        self.db.refresh(account)
        return account

    def soft_delete(self, account: ChartOfAccount) -> ChartOfAccount:
        """
        Soft delete a chart of account.

        Args:
            account: ChartOfAccount object to delete

        Returns:
            Deleted ChartOfAccount object
        """
        from datetime import UTC, datetime

        account.deleted_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(account)
        return account

    def list_accounts(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        account_type: AccountType | None = None,
        parent_account_id: UUID | None = None,
        is_active: bool | None = None,
        is_group: bool | None = None,
        search: str | None = None,
        sort_by: str = "account_code",
        sort_order: str = "asc",
    ) -> tuple[list[ChartOfAccount], int]:
        """
        List chart of accounts with pagination and filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            account_type: Filter by account type
            parent_account_id: Filter by parent account
            is_active: Filter by active status
            is_group: Filter by is_group
            search: Search term for code, name
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of accounts, total count)
        """
        query = self.db.query(ChartOfAccount).filter(
            ChartOfAccount.organization_id == organization_id,
            ChartOfAccount.deleted_at.is_(None),
        )

        if account_type is not None:
            query = query.filter(ChartOfAccount.account_type == account_type)

        if parent_account_id is not None:
            query = query.filter(
                ChartOfAccount.parent_account_id == parent_account_id
            )

        if is_active is not None:
            query = query.filter(ChartOfAccount.is_active == is_active)

        if is_group is not None:
            query = query.filter(ChartOfAccount.is_group == is_group)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    ChartOfAccount.account_code.ilike(search_term),
                    ChartOfAccount.account_name.ilike(search_term),
                )
            )

        total_count = query.count()

        sort_column = getattr(ChartOfAccount, sort_by, ChartOfAccount.account_code)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        offset = (page - 1) * page_size
        accounts = query.offset(offset).limit(page_size).all()

        return accounts, total_count

    def account_code_exists(
        self, account_code: str, organization_id: UUID
    ) -> bool:
        """
        Check if account code already exists in the organization.

        Args:
            account_code: Account code to check
            organization_id: Organization UUID

        Returns:
            True if code exists, False otherwise
        """
        return (
            self.db.query(ChartOfAccount)
            .filter(
                ChartOfAccount.account_code == account_code,
                ChartOfAccount.organization_id == organization_id,
                ChartOfAccount.deleted_at.is_(None),
            )
            .count()
            > 0
        )

    def get_all_accounts(self, organization_id: UUID) -> list[ChartOfAccount]:
        """
        Get all chart of accounts for an organization (for tree building).

        Args:
            organization_id: Organization UUID

        Returns:
            List of all chart of accounts
        """
        return (
            self.db.query(ChartOfAccount)
            .filter(
                ChartOfAccount.organization_id == organization_id,
                ChartOfAccount.deleted_at.is_(None),
            )
            .order_by(ChartOfAccount.account_code)
            .all()
        )

    def has_children(
        self, account_id: UUID, organization_id: UUID
    ) -> bool:
        """
        Check if chart of account has child accounts.

        Args:
            account_id: Chart of account UUID
            organization_id: Organization UUID

        Returns:
            True if has children, False otherwise
        """
        return (
            self.db.query(ChartOfAccount)
            .filter(
                ChartOfAccount.parent_account_id == account_id,
                ChartOfAccount.organization_id == organization_id,
                ChartOfAccount.deleted_at.is_(None),
            )
            .count()
            > 0
        )
