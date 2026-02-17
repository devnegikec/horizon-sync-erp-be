"""Chart of Account service with business logic"""

import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    CannotDeleteException,
    ChartOfAccountNotFoundException,
    CircularReferenceException,
    DuplicateAccountCodeException,
    ValidationError,
)
from app.models.base import AccountStatus, AccountType
from app.models.chart_of_account import Account
from app.repositories.chart_of_account_repository import AccountRepository
from app.schemas.chart_of_account import (
    ChartOfAccountCreate,
    ChartOfAccountTreeNode,
    ChartOfAccountUpdate,
)


class ChartOfAccountService:
    """Service for chart of account operations"""

    # Default account code format pattern (can be overridden via configuration)
    DEFAULT_ACCOUNT_CODE_PATTERN = r"^[A-Za-z0-9\-]+$"

    def __init__(self, db: Session, account_code_pattern: str | None = None):
        self.db = db
        self.repo = AccountRepository(db)
        self.account_code_pattern = account_code_pattern or self.DEFAULT_ACCOUNT_CODE_PATTERN

    def _validate_required_fields(self, account_code: str, account_name: str, account_type: str | None) -> None:
        """
        Validate required fields for account creation.

        Args:
            account_code: Account code to validate
            account_name: Account name to validate
            account_type: Account type to validate

        Raises:
            ValidationError: If any required field is missing or invalid
        """
        errors = []

        if not account_code or not account_code.strip():
            errors.append("Account code is required and cannot be empty")

        if not account_name or not account_name.strip():
            errors.append("Account name is required and cannot be empty")

        if not account_type or not account_type.strip():
            errors.append("Account type is required and cannot be empty")

        if errors:
            raise ValidationError("; ".join(errors))

    def _validate_field_lengths(self, account_code: str, account_name: str) -> None:
        """
        Validate field length constraints.

        Args:
            account_code: Account code to validate (max 50 chars)
            account_name: Account name to validate (max 200 chars)

        Raises:
            ValidationError: If field lengths exceed limits
        """
        errors = []

        if len(account_code) > 50:
            errors.append(f"Account code must not exceed 50 characters (got {len(account_code)})")

        if len(account_name) > 200:
            errors.append(f"Account name must not exceed 200 characters (got {len(account_name)})")

        if errors:
            raise ValidationError("; ".join(errors))

    def _validate_account_code_format(self, account_code: str) -> None:
        """
        Validate account code against configured format pattern.

        Args:
            account_code: Account code to validate

        Raises:
            ValidationError: If account code doesn't match the configured pattern
        """
        if not re.match(self.account_code_pattern, account_code):
            raise ValidationError(
                f"Account code '{account_code}' does not match the required format pattern: {self.account_code_pattern}"
            )

    def create(
        self,
        data: ChartOfAccountCreate,
        organization_id: UUID,
        user_id: UUID,
    ) -> Account:
        """
        Create a new chart of account.

        Args:
            data: Chart of account creation data
            organization_id: Organization UUID
            user_id: User UUID creating the account

        Returns:
            Created Account object

        Raises:
            ValidationError: If validation fails
            DuplicateAccountCodeException: If account code already exists
            ChartOfAccountNotFoundException: If parent account not found
        """
        # Validate required fields
        self._validate_required_fields(
            data.account_code,
            data.account_name,
            data.account_type
        )

        # Validate field lengths
        self._validate_field_lengths(data.account_code, data.account_name)

        # Validate account code format
        self._validate_account_code_format(data.account_code)

        # Check for duplicate account code
        if self.repo.account_code_exists(data.account_code, organization_id):
            raise DuplicateAccountCodeException(
                f"Account with code '{data.account_code}' already exists"
            )

        # Validate parent account if specified
        if data.parent_account_id:
            parent = self.repo.get_by_id(data.parent_account_id, organization_id)
            if not parent:
                raise ChartOfAccountNotFoundException(
                    f"Parent account with ID {data.parent_account_id} not found"
                )

        account_dict = data.model_dump()
        
        # Remove fields that don't exist in the Account model
        fields_to_remove = ['level', 'is_group', 'opening_balance', 'current_balance', 'tags', 'extra_data', 'is_active']
        for field in fields_to_remove:
            account_dict.pop(field, None)
        
        # Add organization_id
        account_dict["organization_id"] = organization_id
        account_dict["created_by"] = str(user_id)
        account_dict["updated_by"] = str(user_id)

        if account_dict.get("account_type"):
            try:
                account_dict["account_type"] = AccountType(
                    str(account_dict["account_type"]).lower()
                )
            except (ValueError, KeyError):
                raise ValidationError(
                    "account_type must be one of: asset, liability, equity, income, expense"
                )

        return self.repo.create(account_dict)

    def get_by_id(
        self,
        account_id: UUID,
        organization_id: UUID,
        include_parent: bool = True,
    ) -> Account:
        """
        Get chart of account by ID.

        Args:
            account_id: Chart of account UUID
            organization_id: Organization UUID
            include_parent: Whether to include parent relationship

        Returns:
            Account object

        Raises:
            ChartOfAccountNotFoundException: If account not found
        """
        if include_parent:
            account = self.repo.get_with_parent(account_id, organization_id)
        else:
            account = self.repo.get_by_id(account_id, organization_id)
            
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
        user_id: UUID | None = None,
    ) -> Account:
        """
        Update a chart of account.

        Args:
            account_id: Chart of account UUID
            data: Chart of account update data
            organization_id: Organization UUID
            user_id: User UUID updating the account

        Returns:
            Updated Account object

        Raises:
            ValidationError: If validation fails
            ChartOfAccountNotFoundException: If account not found
            CircularReferenceException: If parent would create circular reference
        """
        account = self.repo.get_by_id(account_id, organization_id)
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Chart of account with ID {account_id} not found"
            )

        update_dict = data.model_dump(exclude_unset=True)
        
        # Remove fields that don't exist in the Account model
        fields_to_remove = ['level', 'is_group', 'opening_balance', 'current_balance', 'tags', 'extra_data', 'is_active']
        for field in fields_to_remove:
            update_dict.pop(field, None)

        # Validate field lengths if being updated
        if "account_name" in update_dict and update_dict["account_name"]:
            if len(update_dict["account_name"]) > 200:
                raise ValidationError(
                    f"Account name must not exceed 200 characters (got {len(update_dict['account_name'])})"
                )
            if not update_dict["account_name"].strip():
                raise ValidationError("Account name cannot be empty")

        if "parent_account_id" in update_dict and update_dict["parent_account_id"]:
            parent_id = update_dict["parent_account_id"]

            if parent_id == account_id:
                raise CircularReferenceException("Account cannot be its own parent")

            parent = self.repo.get_by_id(parent_id, organization_id)
            if not parent:
                raise ChartOfAccountNotFoundException(
                    f"Parent account with ID {parent_id} not found"
                )

            if self._would_create_circular_reference(account_id, parent_id, organization_id):
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

        if user_id:
            update_dict["updated_by"] = str(user_id)

        return self.repo.update(account, update_dict)

    def delete(
        self,
        account_id: UUID,
        organization_id: UUID,
        user_id: UUID | None = None,
        force: bool = False,
    ) -> None:
        """
        Delete a chart of account.

        Args:
            account_id: Chart of account UUID
            organization_id: Organization UUID
            user_id: User UUID deleting the account (unused, for API compatibility)
            force: If True, delete even if has children

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

        self.repo.delete(account, check_children=not force)

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
    ) -> tuple[list[Account], dict]:
        """
        Get paginated list of chart of accounts with filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            account_type: Filter by type (asset, liability, equity, income, expense)
            parent_account_id: Filter by parent account
            is_active: Filter by active status (unused)
            is_group: Filter by is_group (unused)
            search: Search term
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of accounts, pagination metadata)
        """
        page_size = min(page_size, 1000)

        type_enum = None
        if account_type:
            try:
                type_enum = AccountType(str(account_type).lower())
            except (ValueError, KeyError):
                pass

        status_enum = None
        if is_active is not None:
            status_enum = AccountStatus.ACTIVE if is_active else AccountStatus.INACTIVE

        # Use repository list_all method
        accounts = self.repo.list_all(
            organization_id=organization_id,
            account_type=type_enum,
            status=status_enum,
            parent_account_id=parent_account_id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Simple pagination
        total_count = len(accounts)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_accounts = accounts[start_idx:end_idx]

        total_pages = (total_count + page_size - 1) // page_size
        pagination = {
            "page": page,
            "page_size": page_size,
            "total": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

        return paginated_accounts, pagination

    def get_tree(self, organization_id: UUID) -> list[ChartOfAccountTreeNode]:
        """
        Get chart of accounts as a tree structure.

        Args:
            organization_id: Organization UUID

        Returns:
            List of root-level account tree nodes
        """
        all_accounts = self.repo.list_all(organization_id=organization_id)

        root_nodes = []
        children_map: dict[UUID, list] = {}

        for account in all_accounts:
            if account.parent_account_id:
                if account.parent_account_id not in children_map:
                    children_map[account.parent_account_id] = []
                children_map[account.parent_account_id].append(account)
            else:
                root_nodes.append(account)

        def build_node(acc: Account) -> ChartOfAccountTreeNode:
            children = children_map.get(acc.id, [])
            return ChartOfAccountTreeNode(
                id=acc.id,
                account_code=acc.account_code,
                account_name=acc.account_name,
                account_type=str(acc.account_type.value) if acc.account_type else "",
                status=str(acc.status.value) if acc.status else "active",
                is_posting_account=acc.is_posting_account,
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

    def activate_account(
        self,
        account_id: UUID,
        organization_id: UUID,
        user_id: UUID | None = None,
    ) -> Account:
        """
        Activate an account.

        Args:
            account_id: Account UUID to activate
            organization_id: Organization UUID
            user_id: User UUID performing the action

        Returns:
            Updated Account object with ACTIVE status

        Raises:
            ChartOfAccountNotFoundException: If account not found
        """
        account = self.repo.get_by_id(account_id, organization_id)
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Chart of account with ID {account_id} not found"
            )

        update_dict = {"status": AccountStatus.ACTIVE}
        if user_id:
            update_dict["updated_by"] = str(user_id)

        return self.repo.update(account, update_dict)

    def deactivate_account(
        self,
        account_id: UUID,
        organization_id: UUID,
        user_id: UUID | None = None,
    ) -> Account:
        """
        Deactivate an account.

        Args:
            account_id: Account UUID to deactivate
            organization_id: Organization UUID
            user_id: User UUID performing the action

        Returns:
            Updated Account object with INACTIVE status

        Raises:
            ChartOfAccountNotFoundException: If account not found
        """
        account = self.repo.get_by_id(account_id, organization_id)
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Chart of account with ID {account_id} not found"
            )

        update_dict = {"status": AccountStatus.INACTIVE}
        if user_id:
            update_dict["updated_by"] = str(user_id)

        return self.repo.update(account, update_dict)

    def archive_account(
        self,
        account_id: UUID,
        organization_id: UUID,
        user_id: UUID | None = None,
    ) -> Account:
        """
        Archive an account.

        Args:
            account_id: Account UUID to archive
            organization_id: Organization UUID
            user_id: User UUID performing the action

        Returns:
            Updated Account object with ARCHIVED status

        Raises:
            ChartOfAccountNotFoundException: If account not found
        """
        account = self.repo.get_by_id(account_id, organization_id)
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Chart of account with ID {account_id} not found"
            )

        update_dict = {"status": AccountStatus.ARCHIVED}
        if user_id:
            update_dict["updated_by"] = str(user_id)

        return self.repo.update(account, update_dict)

    def validate_posting_account(
        self,
        account_id: UUID,
        organization_id: UUID,
    ) -> None:
        """
        Validate that an account can receive transaction postings.

        Args:
            account_id: Account UUID to validate
            organization_id: Organization UUID

        Raises:
            ChartOfAccountNotFoundException: If account not found
            ValidationError: If account is inactive or not a posting account
        """
        account = self.repo.get_by_id(account_id, organization_id)
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Chart of account with ID {account_id} not found"
            )

        if account.status != AccountStatus.ACTIVE:
            raise ValidationError(
                f"Cannot post to inactive account '{account.account_code}' (status: {account.status.value})"
            )

        if not account.is_posting_account:
            raise ValidationError(
                f"Cannot post to non-posting account '{account.account_code}' (parent accounts cannot receive postings)"
            )

    # Hierarchy methods

    def get_children(
        self,
        account_id: UUID,
        organization_id: UUID,
    ) -> list[Account]:
        """
        Get all direct child accounts of a parent account.

        Args:
            account_id: Parent account UUID
            organization_id: Organization UUID

        Returns:
            List of child accounts

        Raises:
            ChartOfAccountNotFoundException: If account not found
        """
        from app.services.hierarchy_manager import HierarchyManager

        hierarchy_manager = HierarchyManager(self.db)
        return hierarchy_manager.get_children(account_id, organization_id)

    def get_ancestors(
        self,
        account_id: UUID,
        organization_id: UUID,
    ) -> list[Account]:
        """
        Get all ancestor accounts from the account up to the root.

        Args:
            account_id: Account UUID
            organization_id: Organization UUID

        Returns:
            List of ancestor accounts ordered from immediate parent to root

        Raises:
            ChartOfAccountNotFoundException: If account not found
        """
        from app.services.hierarchy_manager import HierarchyManager

        hierarchy_manager = HierarchyManager(self.db)
        return hierarchy_manager.get_ancestors(account_id, organization_id)

    def get_descendants(
        self,
        account_id: UUID,
        organization_id: UUID,
    ) -> list[Account]:
        """
        Get all descendant accounts recursively.

        Args:
            account_id: Account UUID
            organization_id: Organization UUID

        Returns:
            List of all descendant accounts (children, grandchildren, etc.)

        Raises:
            ChartOfAccountNotFoundException: If account not found
        """
        from app.services.hierarchy_manager import HierarchyManager

        hierarchy_manager = HierarchyManager(self.db)
        return hierarchy_manager.get_descendants(account_id, organization_id)

    def move_account(
        self,
        account_id: UUID,
        new_parent_id: UUID,
        organization_id: UUID,
        user_id: UUID | None = None,
    ) -> Account:
        """
        Move an account to a new parent.

        Args:
            account_id: Account UUID to move
            new_parent_id: New parent account UUID
            organization_id: Organization UUID
            user_id: User UUID performing the action

        Returns:
            Updated Account object

        Raises:
            ChartOfAccountNotFoundException: If account or new parent not found
            CircularReferenceException: If move would create circular reference
            ValidationError: If account types don't match
        """
        from app.services.hierarchy_manager import HierarchyManager

        hierarchy_manager = HierarchyManager(self.db)
        hierarchy_manager.move_account(account_id, new_parent_id, organization_id)

        # Return the updated account
        return self.get_by_id(account_id, organization_id, include_parent=True)

