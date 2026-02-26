"""Chart of Account service with business logic"""

import logging
import re
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

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
        
        # Import CurrencyService for currency validation
        from app.services.currency_service import CurrencyService
        self.currency_service = CurrencyService(db)
        
        # Import AuditLogger for audit trail
        from app.services.audit_logger import AuditLogger
        self.audit_logger = AuditLogger(db)

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

    def _validate_currency(self, currency: str) -> None:
        """
        Validate currency code format.

        Args:
            currency: Currency code to validate (ISO 4217 format)

        Raises:
            ValidationError: If currency code is invalid
        """
        if not currency or len(currency) != 3 or not currency.isupper() or not currency.isalpha():
            raise ValidationError(
                f"Invalid currency code '{currency}'. Must be 3 uppercase letters (ISO 4217 format)"
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

        # Validate currency if provided
        if data.currency:
            self._validate_currency(data.currency)

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
            # Validate parent account is active (Requirement 11.3)
            if parent.status != AccountStatus.ACTIVE:
                raise ValidationError(
                    f"Parent account '{parent.account_code}' must be active. Current status: {parent.status.value}"
                )

        account_dict = data.model_dump()
        
        # Remove fields that don't exist in the Account model or are calculated
        fields_to_remove = ['opening_balance', 'current_balance', 'tags', 'extra_data', 'is_active']
        for field in fields_to_remove:
            account_dict.pop(field, None)
        
        # Calculate hierarchy fields
        level = 1
        is_group = False  # Default to false, set to true if has children later
        
        if data.parent_account_id:
            parent = self.repo.get_by_id(data.parent_account_id, organization_id)
            if parent:
                # Set level to parent level + 1, or default to 1 if parent level doesn't exist
                level = getattr(parent, 'level', 0) + 1
        
        # Set calculated fields
        account_dict['level'] = level
        account_dict['is_group'] = is_group
        
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
                    "account_type must be one of: asset, liability, equity, revenue, expense"
                )

        if account_dict.get("status"):
            try:
                account_dict["status"] = AccountStatus(str(account_dict["status"]).upper())
            except (ValueError, KeyError):
                raise ValidationError(
                    "status must be one of: active, inactive, archived"
                )

        account = self.repo.create(account_dict)
        
        # Log account creation
        from app.models.account_audit_log import AuditAction
        self.audit_logger.log_account_change(
            account_id=account.id,
            action=AuditAction.CREATE,
            user_id=str(user_id),
            new_values={
                "account_code": account.account_code,
                "account_name": account.account_name,
                "account_type": account.account_type.value if account.account_type else None,
                "parent_account_id": str(account.parent_account_id) if account.parent_account_id else None,
                "currency": account.currency,
                "status": account.status.value if account.status else None,
                "is_posting_account": account.is_posting_account,
                "description": account.description,
            }
        )
        
        return account

    def get_by_id(
        self,
        account_id: UUID,
        organization_id: UUID,
        include_parent: bool = True,
        use_cache: bool = True,
    ) -> Account:
        """
        Get chart of account by ID with optional caching.

        Args:
            account_id: Chart of account UUID
            organization_id: Organization UUID
            include_parent: Whether to include parent relationship
            use_cache: Whether to use Redis cache (default: True)

        Returns:
            Account object

        Raises:
            ChartOfAccountNotFoundException: If account not found
        """
        # Try cache first if enabled and not including parent
        if use_cache and not include_parent:
            from app.core.cache import cache, get_account_cache_key
            cache_key = get_account_cache_key(account_id)
            cached_data = cache.get(cache_key)
            if cached_data:
                # Reconstruct account from cached data
                account = Account(**cached_data)
                return account
        
        # Fetch from database
        if include_parent:
            account = self.repo.get_with_parent(account_id, organization_id)
        else:
            account = self.repo.get_by_id(account_id, organization_id)
            
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Chart of account with ID {account_id} not found"
            )
        
        # Cache the account data if enabled and not including parent
        if use_cache and not include_parent:
            from app.core.cache import cache, get_account_cache_key
            cache_key = get_account_cache_key(account_id)
            # Convert account to dict for caching
            account_dict = {
                "id": str(account.id),
                "organization_id": str(account.organization_id),
                "account_code": account.account_code,
                "account_name": account.account_name,
                "account_type": account.account_type.value if account.account_type else None,
                "parent_account_id": str(account.parent_account_id) if account.parent_account_id else None,
                "currency": account.currency,
                "status": account.status.value if account.status else None,
                "is_posting_account": account.is_posting_account,
                "description": account.description,
                "created_by": account.created_by,
                "updated_by": account.updated_by,
                "created_at": account.created_at.isoformat() if account.created_at else None,
                "updated_at": account.updated_at.isoformat() if account.updated_at else None,
            }
            cache.set(cache_key, account_dict, ttl=3600)  # Cache for 1 hour
        
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

        # Validate currency if being updated
        if "currency" in update_dict and update_dict["currency"]:
            self._validate_currency(update_dict["currency"])

        if "parent_account_id" in update_dict and update_dict["parent_account_id"]:
            parent_id = update_dict["parent_account_id"]

            if parent_id == account_id:
                raise CircularReferenceException("Account cannot be its own parent")

            parent = self.repo.get_by_id(parent_id, organization_id)
            if not parent:
                raise ChartOfAccountNotFoundException(
                    f"Parent account with ID {parent_id} not found"
                )
            
            # Validate parent account is active (Requirement 11.3)
            if parent.status != AccountStatus.ACTIVE:
                raise ValidationError(
                    f"Parent account '{parent.account_code}' must be active. Current status: {parent.status.value}"
                )

            if self._would_create_circular_reference(account_id, parent_id, organization_id):
                raise CircularReferenceException(
                    "This parent assignment would create a circular reference"
                )

        if "account_type" in update_dict and update_dict["account_type"]:
            try:
                new_account_type = AccountType(
                    str(update_dict["account_type"]).lower()
                )
            except (ValueError, KeyError):
                # Invalid account type value, remove from update
                del update_dict["account_type"]
            else:
                # Check if account type is being changed
                if account.account_type != new_account_type:
                    # Prevent type change if account has transactions (Requirement 11.6)
                    if self._has_transactions(account_id, organization_id):
                        raise ValidationError(
                            f"Cannot change account type for account '{account.account_code}' "
                            "because it has existing transactions. Account type is immutable once transactions exist."
                        )
                
                update_dict["account_type"] = new_account_type

        if "status" in update_dict and update_dict["status"]:
            try:
                update_dict["status"] = AccountStatus(str(update_dict["status"]).upper())
            except (ValueError, KeyError):
                raise ValidationError(
                    "status must be one of: active, inactive, archived"
                )

        if user_id:
            update_dict["updated_by"] = str(user_id)

        # Capture old values before update for audit trail
        old_values = {
            "account_code": account.account_code,
            "account_name": account.account_name,
            "account_type": account.account_type.value if account.account_type else None,
            "parent_account_id": str(account.parent_account_id) if account.parent_account_id else None,
            "currency": account.currency,
            "status": account.status.value if account.status else None,
            "is_posting_account": account.is_posting_account,
            "description": account.description,
        }

        updated_account = self.repo.update(account, update_dict)
        
        # Invalidate cache for this account
        from app.core.cache import invalidate_account_cache
        invalidate_account_cache(account.id, organization_id)
        
        # Capture new values after update
        new_values = {
            "account_code": updated_account.account_code,
            "account_name": updated_account.account_name,
            "account_type": updated_account.account_type.value if updated_account.account_type else None,
            "parent_account_id": str(updated_account.parent_account_id) if updated_account.parent_account_id else None,
            "currency": updated_account.currency,
            "status": updated_account.status.value if updated_account.status else None,
            "is_posting_account": updated_account.is_posting_account,
            "description": updated_account.description,
        }
        
        # Log account update
        from app.models.account_audit_log import AuditAction
        self.audit_logger.log_account_change(
            account_id=account.id,
            action=AuditAction.UPDATE,
            user_id=str(user_id) if user_id else "system",
            old_values=old_values,
            new_values=new_values,
        )
        
        return updated_account

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

        # Capture account values before deletion for audit trail
        old_values = {
            "account_code": account.account_code,
            "account_name": account.account_name,
            "account_type": account.account_type.value if account.account_type else None,
            "parent_account_id": str(account.parent_account_id) if account.parent_account_id else None,
            "currency": account.currency,
            "status": account.status.value if account.status else None,
            "is_posting_account": account.is_posting_account,
            "description": account.description,
        }

        # Delete the account first
        self.repo.delete(account, check_children=not force)
        
        # Invalidate cache for this account
        from app.core.cache import invalidate_account_cache
        invalidate_account_cache(account_id, organization_id)
        
        # Log account deletion AFTER deleting (audit log will be cascade deleted with account)
        # Note: In production, audit logs should be retained even after account deletion
        # This would require removing the foreign key constraint or using a different approach
        from app.models.account_audit_log import AuditAction
        try:
            self.audit_logger.log_account_change(
                account_id=account_id,
                action=AuditAction.DELETE,
                user_id=str(user_id) if user_id else "system",
                old_values=old_values,
            )
        except Exception:
            # Ignore audit log errors for deletions since the account no longer exists
            pass

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        account_type: str | None = None,
        parent_account_id: UUID | None = None,
        is_active: bool | None = None,
        is_group: bool | None = None,
        currency: str | None = None,
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
            account_type: Filter by type (asset, liability, equity, revenue, expense)
            parent_account_id: Filter by parent account
            is_active: Filter by active status (unused)
            is_group: Filter by is_group (unused)
            currency: Filter by currency code
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

        # Calculate offset for pagination
        offset = (page - 1) * page_size

        # Get total count for pagination metadata
        total_count = self.repo.count_all(
            organization_id=organization_id,
            account_type=type_enum,
            status=status_enum,
            parent_account_id=parent_account_id,
            search=search,
        )

        # Get paginated accounts using limit/offset
        accounts = self.repo.list_all(
            organization_id=organization_id,
            account_type=type_enum,
            status=status_enum,
            parent_account_id=parent_account_id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=page_size,
            offset=offset,
        )
        
        # Apply currency filter if provided (post-query filter)
        if currency:
            accounts = [a for a in accounts if a.currency == currency]
            # Recalculate total for currency filter
            all_accounts = self.repo.list_all(
                organization_id=organization_id,
                account_type=type_enum,
                status=status_enum,
                parent_account_id=parent_account_id,
                search=search,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            total_count = len([a for a in all_accounts if a.currency == currency])

        # Add balance calculation for each account
        from app.services.balance_calculator import BalanceCalculator
        balance_calculator = BalanceCalculator(self.db)
        
        for account in accounts:
            try:
                balance_info = balance_calculator.calculate_balance(account.id)
                if balance_info:
                    # Set current_balance as an attribute so Pydantic can serialize it
                    account.current_balance = float(balance_info.get('balance', 0))
                else:
                    account.current_balance = 0.0
            except Exception as e:
                # Log error but don't fail the entire request
                logger.warning(f"Failed to calculate balance for account {account.id}: {e}")
                account.current_balance = 0.0

        total_pages = (total_count + page_size - 1) // page_size
        pagination = {
            "page": page,
            "page_size": page_size,
            "total": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

        return accounts, pagination

    def get_tree(self, organization_id: UUID, use_cache: bool = True) -> list[ChartOfAccountTreeNode]:
        """
        Get chart of accounts as a tree structure with optional caching.

        Args:
            organization_id: Organization UUID
            use_cache: Whether to use Redis cache (default: True)

        Returns:
            List of root-level account tree nodes
        """
        # Try cache first if enabled
        if use_cache:
            from app.core.cache import cache, get_account_tree_cache_key
            cache_key = get_account_tree_cache_key(organization_id)
            cached_tree = cache.get(cache_key)
            if cached_tree:
                # Reconstruct tree nodes from cached data
                return [ChartOfAccountTreeNode(**node) for node in cached_tree]
        
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

        tree = [build_node(a) for a in root_nodes]
        
        # Cache the tree if enabled
        if use_cache:
            from app.core.cache import cache, get_account_tree_cache_key
            cache_key = get_account_tree_cache_key(organization_id)
            # Convert tree to dict for caching
            tree_dict = [node.model_dump() for node in tree]
            cache.set(cache_key, tree_dict, ttl=1800)  # Cache for 30 minutes
        
        return tree

    def get_tree_roots(self, organization_id: UUID) -> list[ChartOfAccountTreeNode]:
        """
        Get only root-level accounts for lazy loading.

        Args:
            organization_id: Organization UUID

        Returns:
            List of root-level account tree nodes without children
        """
        # Get only root accounts (no parent)
        root_accounts = self.repo.list_all(
            organization_id=organization_id,
            parent_account_id=None,
            sort_by="account_code",
            sort_order="asc",
        )

        # Build tree nodes without children
        tree_nodes = []
        for account in root_accounts:
            # Check if account has children
            has_children = self.repo.has_children(account.id, organization_id)
            
            node = ChartOfAccountTreeNode(
                id=account.id,
                account_code=account.account_code,
                account_name=account.account_name,
                account_type=str(account.account_type.value) if account.account_type else "",
                status=str(account.status.value) if account.status else "active",
                is_posting_account=account.is_posting_account,
                children=[] if has_children else [],  # Empty list indicates children can be loaded
            )
            tree_nodes.append(node)

        return tree_nodes

    def get_tree_children(self, account_id: UUID, organization_id: UUID) -> list[ChartOfAccountTreeNode]:
        """
        Get immediate children of an account as tree nodes for lazy loading.

        Args:
            account_id: Parent account UUID
            organization_id: Organization UUID

        Returns:
            List of immediate child account tree nodes

        Raises:
            ChartOfAccountNotFoundException: If account not found
        """
        # Validate account exists
        account = self.repo.get_by_id(account_id, organization_id)
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Account with ID {account_id} not found"
            )

        # Get immediate children
        children = self.repo.get_children(account_id, organization_id)

        # Build tree nodes
        tree_nodes = []
        for child in children:
            # Check if child has children
            has_children = self.repo.has_children(child.id, organization_id)
            
            node = ChartOfAccountTreeNode(
                id=child.id,
                account_code=child.account_code,
                account_name=child.account_name,
                account_type=str(child.account_type.value) if child.account_type else "",
                status=str(child.status.value) if child.status else "active",
                is_posting_account=child.is_posting_account,
                children=[] if has_children else [],  # Empty list indicates children can be loaded
            )
            tree_nodes.append(node)

        return tree_nodes

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

        # Capture old status
        old_status = account.status.value if account.status else None

        updated_account = self.repo.update(account, update_dict)
        
        # Log status change
        from app.models.account_audit_log import AuditAction
        self.audit_logger.log_account_change(
            account_id=account.id,
            action=AuditAction.STATUS_CHANGE,
            user_id=str(user_id) if user_id else "system",
            old_values={"status": old_status},
            new_values={"status": AccountStatus.ACTIVE.value},
        )
        
        return updated_account

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

        # Capture old status
        old_status = account.status.value if account.status else None

        updated_account = self.repo.update(account, update_dict)
        
        # Log status change
        from app.models.account_audit_log import AuditAction
        self.audit_logger.log_account_change(
            account_id=account.id,
            action=AuditAction.STATUS_CHANGE,
            user_id=str(user_id) if user_id else "system",
            old_values={"status": old_status},
            new_values={"status": AccountStatus.INACTIVE.value},
        )
        
        return updated_account

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

        # Capture old status
        old_status = account.status.value if account.status else None

        updated_account = self.repo.update(account, update_dict)
        
        # Log status change
        from app.models.account_audit_log import AuditAction
        self.audit_logger.log_account_change(
            account_id=account.id,
            action=AuditAction.STATUS_CHANGE,
            user_id=str(user_id) if user_id else "system",
            old_values={"status": old_status},
            new_values={"status": AccountStatus.ARCHIVED.value},
        )
        
        return updated_account

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
    def _has_transactions(self, account_id: UUID, organization_id: UUID) -> bool:
        """
        Check if an account has any transactions posted to it.

        Args:
            account_id: Account UUID
            organization_id: Organization UUID

        Returns:
            True if account has transactions, False otherwise

        Note:
            This is a placeholder implementation. When the general ledger/journal entry
            system is implemented, this method should query the transaction tables.
            For now, it returns False to allow type changes until transactions exist.
        """
        # TODO: Implement actual transaction check when general ledger is added
        # Example query when transactions table exists:
        # from app.models.journal_entry import JournalEntry
        # return self.db.query(JournalEntry).filter(
        #     JournalEntry.account_id == account_id,
        #     JournalEntry.organization_id == organization_id
        # ).first() is not None

        return False


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

    # Bulk operations

    def bulk_activate_accounts(
        self,
        account_ids: list[UUID],
        organization_id: UUID,
        user_id: UUID | None = None,
    ) -> dict:
        """
        Activate multiple accounts in bulk.

        Args:
            account_ids: List of account UUIDs to activate
            organization_id: Organization UUID
            user_id: User UUID performing the action

        Returns:
            Dictionary with success count, failed count, and error details
        """
        results = {
            "success_count": 0,
            "failed_count": 0,
            "errors": [],
            "updated_ids": []
        }

        for account_id in account_ids:
            try:
                self.activate_account(account_id, organization_id, user_id)
                results["success_count"] += 1
                results["updated_ids"].append(str(account_id))
            except Exception as e:
                results["failed_count"] += 1
                results["errors"].append({
                    "account_id": str(account_id),
                    "error": str(e)
                })

        return results

    def bulk_deactivate_accounts(
        self,
        account_ids: list[UUID],
        organization_id: UUID,
        user_id: UUID | None = None,
    ) -> dict:
        """
        Deactivate multiple accounts in bulk.

        Args:
            account_ids: List of account UUIDs to deactivate
            organization_id: Organization UUID
            user_id: User UUID performing the action

        Returns:
            Dictionary with success count, failed count, and error details
        """
        results = {
            "success_count": 0,
            "failed_count": 0,
            "errors": [],
            "updated_ids": []
        }

        for account_id in account_ids:
            try:
                self.deactivate_account(account_id, organization_id, user_id)
                results["success_count"] += 1
                results["updated_ids"].append(str(account_id))
            except Exception as e:
                results["failed_count"] += 1
                results["errors"].append({
                    "account_id": str(account_id),
                    "error": str(e)
                })

        return results

    def bulk_delete_accounts(
        self,
        account_ids: list[UUID],
        organization_id: UUID,
        user_id: UUID | None = None,
        force: bool = False,
    ) -> dict:
        """
        Delete multiple accounts in bulk with validation.

        Args:
            account_ids: List of account UUIDs to delete
            organization_id: Organization UUID
            user_id: User UUID performing the action
            force: If True, delete even if has children

        Returns:
            Dictionary with success count, failed count, and error details
        """
        results = {
            "success_count": 0,
            "failed_count": 0,
            "errors": [],
            "deleted_ids": []
        }

        for account_id in account_ids:
            try:
                # Validate before deletion
                account = self.repo.get_by_id(account_id, organization_id)
                if not account:
                    results["failed_count"] += 1
                    results["errors"].append({
                        "account_id": str(account_id),
                        "error": "Account not found"
                    })
                    continue

                # Check for children if not forcing
                if not force and self.repo.has_children(account_id, organization_id):
                    results["failed_count"] += 1
                    results["errors"].append({
                        "account_id": str(account_id),
                        "account_code": account.account_code,
                        "error": "Cannot delete account with child accounts"
                    })
                    continue

                # Check for transactions (placeholder for now)
                if self._has_transactions(account_id, organization_id):
                    results["failed_count"] += 1
                    results["errors"].append({
                        "account_id": str(account_id),
                        "account_code": account.account_code,
                        "error": "Cannot delete account with existing transactions"
                    })
                    continue

                self.delete(account_id, organization_id, user_id, force)
                results["success_count"] += 1
                results["deleted_ids"].append(str(account_id))
            except Exception as e:
                results["failed_count"] += 1
                results["errors"].append({
                    "account_id": str(account_id),
                    "error": str(e)
                })

        return results

