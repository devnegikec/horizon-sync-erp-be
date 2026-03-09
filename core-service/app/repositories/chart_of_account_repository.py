"""Account repository for database operations"""

from uuid import UUID

from sqlalchemy import String, cast, func, inspect, or_
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
            .filter(
                Account.id == account_id, Account.organization_id == organization_id
            )
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
                Account.organization_id == organization_id,
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

    def delete(self, account: Account, check_children: bool = True) -> None:
        """
        Delete an account.

        Args:
            account: Account object to delete

        Raises:
            IntegrityError: If account has child accounts (foreign key constraint)
        """
        if check_children:
            has_child_accounts = (
                self.db.query(Account)
                .filter(
                    Account.parent_account_id == account.id,
                    Account.organization_id == account.organization_id,
                )
                .count()
                > 0
            )
            if has_child_accounts:
                raise IntegrityError(
                    "Cannot delete account with child accounts",
                    params=None,
                    orig=None,
                )

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
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Account]:
        """
        List all accounts with optional filtering and pagination.

        Args:
            organization_id: Organization UUID
            account_type: Filter by account type
            status: Filter by account status
            parent_account_id: Filter by parent account
            search: Search term for code or name (case-insensitive)
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of accounts matching the filters
        """
        query = self.db.query(Account).filter(
            Account.organization_id == organization_id
        )

        # Apply filters
        if account_type is not None:
            query = query.filter(
                func.lower(cast(Account.account_type, String))
                == str(account_type.value).lower()
            )

        if status is not None:
            query = query.filter(
                func.lower(cast(Account.status, String)) == str(status.value).lower()
            )

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

        # Apply sorting (schema-aware fallback to avoid runtime DB mismatches)
        allowed_sort_fields = {
            "id",
            "account_code",
            "account_name",
            "account_type",
            "status",
            "created_at",
            "updated_at",
        }
        requested_sort_field = (
            sort_by if sort_by in allowed_sort_fields else "account_code"
        )

        existing_columns: set[str] = set()
        try:
            table_columns = inspect(self.db.get_bind()).get_columns("accounts")
            existing_columns = {column["name"] for column in table_columns}
        except Exception:
            existing_columns = set()

        if existing_columns and requested_sort_field not in existing_columns:
            requested_sort_field = (
                "created_at" if "created_at" in existing_columns else "account_code"
            )

        sort_column = getattr(Account, requested_sort_field, Account.account_code)
        normalized_order = "desc" if str(sort_order).lower() == "desc" else "asc"
        if normalized_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination if limit/offset provided
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def count_all(
        self,
        organization_id: UUID,
        account_type: AccountType | None = None,
        status: AccountStatus | None = None,
        parent_account_id: UUID | None = None,
        search: str | None = None,
    ) -> int:
        """
        Count all accounts matching filters.

        Args:
            organization_id: Organization UUID
            account_type: Filter by account type
            status: Filter by account status
            parent_account_id: Filter by parent account
            search: Search term for code or name (case-insensitive)

        Returns:
            Total count of accounts matching the filters
        """
        query = self.db.query(Account).filter(
            Account.organization_id == organization_id
        )

        # Apply filters (same as list_all)
        if account_type is not None:
            query = query.filter(
                func.lower(cast(Account.account_type, String))
                == str(account_type.value).lower()
            )

        if status is not None:
            query = query.filter(
                func.lower(cast(Account.status, String)) == str(status.value).lower()
            )

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

        return query.count()

    def account_code_exists(
        self, account_code: str, organization_id: UUID, exclude_id: UUID | None = None
    ) -> bool:
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
            Account.organization_id == organization_id,
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
                Account.organization_id == organization_id,
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
                Account.organization_id == organization_id,
            )
            .order_by(Account.account_code)
            .all()
        )

    def get_with_parent(
        self, account_id: UUID, organization_id: UUID
    ) -> Account | None:
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
            .filter(
                Account.id == account_id, Account.organization_id == organization_id
            )
            .first()
        )

    def get_descendants_recursive(
        self, account_id: UUID, organization_id: UUID
    ) -> list[Account]:
        """
        Get all descendant accounts using recursive CTE for optimal performance.

        Args:
            account_id: Parent account UUID
            organization_id: Organization UUID

        Returns:
            List of all descendant accounts
        """
        from sqlalchemy import text

        # Use recursive CTE for efficient hierarchy traversal
        query = text("""
            WITH RECURSIVE account_tree AS (
                -- Base case: direct children
                SELECT id, account_code, account_name, account_type, parent_account_id,
                       currency, status, is_posting_account, description,
                       created_by, updated_by, created_at, updated_at, organization_id,
                       1 as depth
                FROM accounts
                WHERE parent_account_id = :account_id
                  AND organization_id = :organization_id

                UNION ALL

                -- Recursive case: children of children
                SELECT a.id, a.account_code, a.account_name, a.account_type, a.parent_account_id,
                       a.currency, a.status, a.is_posting_account, a.description,
                       a.created_by, a.updated_by, a.created_at, a.updated_at, a.organization_id,
                       at.depth + 1
                FROM accounts a
                INNER JOIN account_tree at ON a.parent_account_id = at.id
                WHERE at.depth < 10  -- Prevent infinite loops
                  AND a.organization_id = :organization_id
            )
            SELECT * FROM account_tree
            ORDER BY depth, account_code
        """)

        result = self.db.execute(
            query,
            {"account_id": str(account_id), "organization_id": str(organization_id)},
        )

        # Convert results to Account objects
        descendants = []
        for row in result.mappings():
            account = Account(
                id=row["id"],
                organization_id=row["organization_id"],
                account_code=row["account_code"],
                account_name=row["account_name"],
                account_type=row["account_type"],
                parent_account_id=row["parent_account_id"],
                currency=row["currency"],
                status=row["status"],
                is_posting_account=row["is_posting_account"],
                description=row["description"],
                created_by=row["created_by"],
                updated_by=row["updated_by"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            descendants.append(account)

        return descendants

    def get_ancestors_recursive(
        self, account_id: UUID, organization_id: UUID
    ) -> list[Account]:
        """
        Get all ancestor accounts using recursive CTE for optimal performance.

        Args:
            account_id: Account UUID
            organization_id: Organization UUID

        Returns:
            List of ancestor accounts ordered from immediate parent to root
        """
        from sqlalchemy import text

        # Use recursive CTE for efficient hierarchy traversal
        query = text("""
            WITH RECURSIVE account_tree AS (
                -- Base case: get the account itself
                SELECT id, account_code, account_name, account_type, parent_account_id,
                       currency, status, is_posting_account, description,
                       created_by, updated_by, created_at, updated_at, organization_id,
                       0 as depth
                FROM accounts
                WHERE id = :account_id
                  AND organization_id = :organization_id

                UNION ALL

                -- Recursive case: get parent
                SELECT a.id, a.account_code, a.account_name, a.account_type, a.parent_account_id,
                       a.currency, a.status, a.is_posting_account, a.description,
                       a.created_by, a.updated_by, a.created_at, a.updated_at, a.organization_id,
                       at.depth + 1
                FROM accounts a
                INNER JOIN account_tree at ON a.id = at.parent_account_id
                WHERE at.depth < 10  -- Prevent infinite loops
                  AND a.organization_id = :organization_id
            )
            SELECT * FROM account_tree
            WHERE depth > 0  -- Exclude the account itself
            ORDER BY depth ASC
        """)

        result = self.db.execute(
            query,
            {"account_id": str(account_id), "organization_id": str(organization_id)},
        )

        # Convert results to Account objects
        ancestors = []
        for row in result.mappings():
            account = Account(
                id=row["id"],
                organization_id=row["organization_id"],
                account_code=row["account_code"],
                account_name=row["account_name"],
                account_type=row["account_type"],
                parent_account_id=row["parent_account_id"],
                currency=row["currency"],
                status=row["status"],
                is_posting_account=row["is_posting_account"],
                description=row["description"],
                created_by=row["created_by"],
                updated_by=row["updated_by"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            ancestors.append(account)

        return ancestors
