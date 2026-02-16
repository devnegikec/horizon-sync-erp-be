"""Account repository for database operations"""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.base import AccountStatus, AccountType
from app.models.chart_of_account import Account


class AccountRepository:
    """Repository for account database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Account:
        """
        Create a new account.

        Args:
            data: Dictionary containing account data (must include organization_id)

        Returns:
            Created Account object

        Raises:
            IntegrityError: If account code already exists for this organization (unique constraint violation)
        """
        account = Account(**data)
        self.db.add(account)
        try:
            self.db.commit()
            self.db.refresh(account)
            return account
        except IntegrityError as e:
            self.db.rollback()
            raise e

    def get_by_id(self, account_id: UUID, organization_id: UUID) -> Account | None:
        """
        Get account by ID.

        Args:
            account_id: Account UUID
            organization_id: Organization UUID

        Returns:
            Account object or None if not found
        """
        return (
            self.db.query(Account)
            .filter(Account.id == account_id, Account.organization_id == organization_id)
            .first()
        )

    def get_by_code(self, account_code: str, organization_id: UUID) -> Account | None:
        """
        Get account by code.

        Args:
            account_code: Account code
            organization_id: Organization UUID

        Returns:
            Account object or None if not found
        """
        return (
            self.db.query(Account)
            .filter(
                Account.account_code == account_code,
                Account.organization_id == organization_id
            )
            .first()
        )

    def update(self, account: Account, update_data: dict) -> Account:
        """
        Update account fields.

        Args:
            account: Account object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated Account object

        Raises:
            IntegrityError: If updated account code already exists
        """
        for key, value in update_data.items():
            if hasattr(account, key):
                setattr(account, key, value)

        try:
            self.db.commit()
            self.db.refresh(account)
            return account
        except IntegrityError as e:
            self.db.rollback()
            raise e

    def delete(self, account: Account) -> None:
        """
        Delete an account.

        Args:
            account: Account object to delete

        Raises:
            IntegrityError: If account has child accounts (foreign key constraint)
        """
        try:
            self.db.delete(account)
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            raise e

    def list_all(
        self,
        organization_id: UUID,
        account_type: AccountType | None = None,
        status: AccountStatus | None = None,
        parent_account_id: UUID | None = None,
        search: str | None = None,
        sort_by: str = "account_code",
        sort_order: str = "asc",
    ) -> list[Account]:
        """
        List all accounts with optional filtering.

        Args:
            organization_id: Organization UUID
            account_type: Filter by account type
            status: Filter by account status
            parent_account_id: Filter by parent account
            search: Search term for code or name (case-insensitive)
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            List of accounts matching the filters
        """
        query = self.db.query(Account).filter(Account.organization_id == organization_id)

        # Apply filters
        if account_type is not None:
            query = query.filter(Account.account_type == account_type)

        if status is not None:
            query = query.filter(Account.status == status)

        if parent_account_id is not None:
            query = query.filter(Account.parent_account_id == parent_account_id)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Account.account_code.ilike(search_term),
                    Account.account_name.ilike(search_term),
                )
            )

        # Apply sorting
        sort_column = getattr(Account, sort_by, Account.account_code)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        return query.all()

    def account_code_exists(self, account_code: str, organization_id: UUID, exclude_id: UUID | None = None) -> bool:
        """
        Check if account code already exists.

        Args:
            account_code: Account code to check
            organization_id: Organization UUID
            exclude_id: Optional account ID to exclude from check (for updates)

        Returns:
            True if code exists, False otherwise
        """
        query = self.db.query(Account).filter(
            Account.account_code == account_code,
            Account.organization_id == organization_id
        )
        
        if exclude_id is not None:
            query = query.filter(Account.id != exclude_id)
        
        return query.count() > 0

    def has_children(self, account_id: UUID, organization_id: UUID) -> bool:
        """
        Check if account has child accounts.

        Args:
            account_id: Account UUID
            organization_id: Organization UUID

        Returns:
            True if has children, False otherwise
        """
        return (
            self.db.query(Account)
            .filter(
                Account.parent_account_id == account_id,
                Account.organization_id == organization_id
            )
            .count()
            > 0
        )

    def get_children(self, account_id: UUID, organization_id: UUID) -> list[Account]:
        """
        Get all child accounts of a parent account.

        Args:
            account_id: Parent account UUID
            organization_id: Organization UUID

        Returns:
            List of child accounts
        """
        return (
            self.db.query(Account)
            .filter(
                Account.parent_account_id == account_id,
                Account.organization_id == organization_id
            )
            .order_by(Account.account_code)
            .all()
        )

    def get_with_parent(self, account_id: UUID, organization_id: UUID) -> Account | None:
        """
        Get account by ID with parent relationship loaded.

        Args:
            account_id: Account UUID
            organization_id: Organization UUID

        Returns:
            Account object with parent loaded, or None if not found
        """
        return (
            self.db.query(Account)
            .options(joinedload(Account.parent_account))
            .filter(Account.id == account_id, Account.organization_id == organization_id)
            .first()
        )
