"""Chart of Account service with business logic"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    CannotDeleteException,
    ChartOfAccountNotFoundException,
    CircularReferenceException,
    DuplicateAccountCodeException,
    ValidationError,
)
from app.models.base import AccountType
from app.models.chart_of_account import ChartOfAccount
from app.repositories.chart_of_account_repository import ChartOfAccountRepository
from app.schemas.chart_of_account import (
    ChartOfAccountCreate,
    ChartOfAccountTreeNode,
    ChartOfAccountUpdate,
)


class ChartOfAccountService:
    """Service for chart of account operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ChartOfAccountRepository(db)

    def create(
        self,
        data: ChartOfAccountCreate,
        organization_id: UUID,
        user_id: UUID,
    ) -> ChartOfAccount:
        """
        Create a new chart of account.

        Args:
            data: Chart of account creation data
            organization_id: Organization UUID
            user_id: User UUID creating the account

        Returns:
            Created ChartOfAccount object

        Raises:
            DuplicateAccountCodeException: If account code already exists
            ChartOfAccountNotFoundException: If parent account not found
        """
        if self.repo.account_code_exists(data.account_code, organization_id):
            raise DuplicateAccountCodeException(
                f"Account with code '{data.account_code}' already exists"
            )

        if data.parent_account_id:
            parent = self.repo.get_by_id(data.parent_account_id, organization_id)
            if not parent:
                raise ChartOfAccountNotFoundException(
                    f"Parent account with ID {data.parent_account_id} not found"
                )

        account_dict = data.model_dump()
        account_dict["organization_id"] = organization_id
        account_dict["created_by"] = user_id
        account_dict["updated_by"] = user_id

        if account_dict.get("account_type"):
            try:
                account_dict["account_type"] = AccountType(
                    str(account_dict["account_type"]).lower()
                )
            except (ValueError, KeyError):
                raise ValidationError(
                    "account_type must be one of: asset, liability, equity, income, expense"
                )

        return self.repo.create_chart_of_account(account_dict)

    def get_by_id(
        self,
        account_id: UUID,
        organization_id: UUID,
        include_parent: bool = True,
    ) -> ChartOfAccount:
        """
        Get chart of account by ID.

        Args:
            account_id: Chart of account UUID
            organization_id: Organization UUID
            include_parent: Whether to include parent relationship

        Returns:
            ChartOfAccount object

        Raises:
            ChartOfAccountNotFoundException: If account not found
        """
        account = self.repo.get_by_id(
            account_id, organization_id, include_parent=include_parent
        )
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Chart of account with ID {account_id} not found"
            )
        return account

    def update(
        self,
        account_id: UUID,
        data: ChartOfAccountUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> ChartOfAccount:
        """
        Update a chart of account.

        Args:
            account_id: Chart of account UUID
            data: Chart of account update data
            organization_id: Organization UUID
            user_id: User UUID updating the account

        Returns:
            Updated ChartOfAccount object

        Raises:
            ChartOfAccountNotFoundException: If account not found
            CircularReferenceException: If parent would create circular reference
        """
        account = self.repo.get_by_id(account_id, organization_id)
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Chart of account with ID {account_id} not found"
            )

        update_dict = data.model_dump(exclude_unset=True)

        if "parent_account_id" in update_dict and update_dict["parent_account_id"]:
            parent_id = update_dict["parent_account_id"]

            if parent_id == account_id:
                raise CircularReferenceException("Account cannot be its own parent")

            parent = self.repo.get_by_id(parent_id, organization_id)
            if not parent:
                raise ChartOfAccountNotFoundException(
                    f"Parent account with ID {parent_id} not found"
                )

            if self._would_create_circular_reference(
                account_id, parent_id, organization_id
            ):
                raise CircularReferenceException(
                    "This parent assignment would create a circular reference"
                )

        if "account_type" in update_dict and update_dict["account_type"]:
            try:
                update_dict["account_type"] = AccountType(
                    str(update_dict["account_type"]).lower()
                )
            except (ValueError, KeyError):
                del update_dict["account_type"]

        update_dict["updated_by"] = user_id

        return self.repo.update(account, update_dict)

    def delete(
        self,
        account_id: UUID,
        organization_id: UUID,
        user_id: UUID,
        force: bool = False,
    ) -> ChartOfAccount:
        """
        Soft delete a chart of account.

        Args:
            account_id: Chart of account UUID
            organization_id: Organization UUID
            user_id: User UUID deleting the account
            force: If True, delete even if has children

        Returns:
            Deleted ChartOfAccount object

        Raises:
            ChartOfAccountNotFoundException: If account not found
            CannotDeleteException: If has children and force=False
        """
        account = self.repo.get_by_id(account_id, organization_id)
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Chart of account with ID {account_id} not found"
            )

        if not force and self.repo.has_children(account_id, organization_id):
            raise CannotDeleteException(
                "Cannot delete account with child accounts. "
                "Delete children first or use force=true."
            )

        account.updated_by = user_id
        return self.repo.soft_delete(account)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        account_type: str | None = None,
        parent_account_id: UUID | None = None,
        is_active: bool | None = None,
        is_group: bool | None = None,
        search: str | None = None,
        sort_by: str = "account_code",
        sort_order: str = "asc",
    ) -> tuple[list[ChartOfAccount], dict]:
        """
        Get paginated list of chart of accounts with filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            account_type: Filter by type (asset, liability, equity, income, expense)
            parent_account_id: Filter by parent account
            is_active: Filter by active status
            is_group: Filter by is_group
            search: Search term
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of accounts, pagination metadata)
        """
        page_size = min(page_size, 100)

        type_enum = None
        if account_type:
            try:
                type_enum = AccountType(str(account_type).lower())
            except (ValueError, KeyError):
                pass

        accounts, total_count = self.repo.list_accounts(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            account_type=type_enum,
            parent_account_id=parent_account_id,
            is_active=is_active,
            is_group=is_group,
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

        return accounts, pagination

    def get_tree(self, organization_id: UUID) -> list[ChartOfAccountTreeNode]:
        """
        Get chart of accounts as a tree structure.

        Args:
            organization_id: Organization UUID

        Returns:
            List of root-level account tree nodes
        """
        all_accounts = self.repo.get_all_accounts(organization_id)

        root_nodes = []
        children_map: dict[UUID, list] = {}

        for account in all_accounts:
            if account.parent_account_id:
                if account.parent_account_id not in children_map:
                    children_map[account.parent_account_id] = []
                children_map[account.parent_account_id].append(account)
            else:
                root_nodes.append(account)

        def build_node(acc: ChartOfAccount) -> ChartOfAccountTreeNode:
            children = children_map.get(acc.id, [])
            return ChartOfAccountTreeNode(
                id=acc.id,
                account_code=acc.account_code,
                account_name=acc.account_name,
                account_type=str(acc.account_type.value) if acc.account_type else "",
                level=acc.level,
                is_group=acc.is_group,
                is_active=acc.is_active,
                children=[build_node(c) for c in children],
            )

        return [build_node(a) for a in root_nodes]

    def _would_create_circular_reference(
        self, account_id: UUID, new_parent_id: UUID, organization_id: UUID
    ) -> bool:
        """
        Check if setting new_parent_id as parent would create circular reference.
        """
        current_id = new_parent_id
        visited = set()

        while current_id:
            if current_id in visited:
                return True
            if current_id == account_id:
                return True

            visited.add(current_id)

            parent = self.repo.get_by_id(current_id, organization_id)
            if not parent:
                break

            current_id = parent.parent_account_id

        return False
