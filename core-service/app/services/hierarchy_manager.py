"""Hierarchy Manager service for Chart of Accounts hierarchy operations"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ChartOfAccountNotFoundException,
    CircularReferenceException,
    ValidationError,
)
from app.models.chart_of_account import Account
from app.repositories.chart_of_account_repository import AccountRepository


class HierarchyManager:
    """Service for managing account hierarchy operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AccountRepository(db)

    def add_child(
        self,
        parent_id: UUID,
        child_id: UUID,
        organization_id: UUID,
    ) -> None:
        """
        Add a child account under a parent account.

        Args:
            parent_id: Parent account UUID
            child_id: Child account UUID
            organization_id: Organization UUID

        Raises:
            ChartOfAccountNotFoundException: If parent or child account not found
            CircularReferenceException: If assignment would create circular reference
            ValidationError: If account types don't match or parent is not active
        """
        # Validate parent exists
        parent = self.repo.get_by_id(parent_id, organization_id)
        if not parent:
            raise ChartOfAccountNotFoundException(
                f"Parent account with ID {parent_id} not found"
            )

        # Validate parent account is active (Requirement 11.3)
        from app.models.base import AccountStatus

        if parent.status != AccountStatus.ACTIVE:
            raise ValidationError(
                f"Parent account '{parent.account_code}' must be active. Current status: {parent.status.value}"
            )

        # Validate child exists
        child = self.repo.get_by_id(child_id, organization_id)
        if not child:
            raise ChartOfAccountNotFoundException(
                f"Child account with ID {child_id} not found"
            )

        # Validate account type consistency
        if parent.account_type != child.account_type:
            raise ValidationError(
                f"Account type mismatch: parent is {parent.account_type.value}, "
                f"child is {child.account_type.value}. "
                "Parent and child accounts must have the same account type."
            )

        # Check for circular reference
        if self.detect_circular_reference(child_id, parent_id, organization_id):
            raise CircularReferenceException(
                "Cannot add child: this would create a circular reference in the hierarchy"
            )

        # Update child's parent
        self.repo.update(child, {"parent_account_id": parent_id})

        # Update parent to be non-posting account (parent accounts cannot receive postings)
        if parent.is_posting_account:
            self.repo.update(parent, {"is_posting_account": False})

    def remove_child(
        self,
        child_id: UUID,
        organization_id: UUID,
    ) -> None:
        """
        Remove a child account from its parent (make it a root account).

        Args:
            child_id: Child account UUID
            organization_id: Organization UUID

        Raises:
            ChartOfAccountNotFoundException: If child account not found
        """
        # Validate child exists
        child = self.repo.get_by_id(child_id, organization_id)
        if not child:
            raise ChartOfAccountNotFoundException(
                f"Child account with ID {child_id} not found"
            )

        # Store old parent ID before removing
        old_parent_id = child.parent_account_id

        # Remove parent reference
        self.repo.update(child, {"parent_account_id": None})

        # If old parent has no more children, make it a posting account
        if old_parent_id and not self.repo.has_children(old_parent_id, organization_id):
            old_parent = self.repo.get_by_id(old_parent_id, organization_id)
            if old_parent:
                self.repo.update(old_parent, {"is_posting_account": True})

    def move_account(
        self,
        account_id: UUID,
        new_parent_id: UUID,
        organization_id: UUID,
    ) -> None:
        """
        Move an account to a new parent.

        Args:
            account_id: Account UUID to move
            new_parent_id: New parent account UUID
            organization_id: Organization UUID

        Raises:
            ChartOfAccountNotFoundException: If account or new parent not found
            CircularReferenceException: If move would create circular reference
            ValidationError: If account types don't match or parent is not active
        """
        # Validate account exists
        account = self.repo.get_by_id(account_id, organization_id)
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Account with ID {account_id} not found"
            )

        # Validate new parent exists
        new_parent = self.repo.get_by_id(new_parent_id, organization_id)
        if not new_parent:
            raise ChartOfAccountNotFoundException(
                f"New parent account with ID {new_parent_id} not found"
            )

        # Validate parent account is active (Requirement 11.3)
        from app.models.base import AccountStatus

        if new_parent.status != AccountStatus.ACTIVE:
            raise ValidationError(
                f"Parent account '{new_parent.account_code}' must be active. Current status: {new_parent.status.value}"
            )

        # Validate account type consistency
        if account.account_type != new_parent.account_type:
            raise ValidationError(
                f"Account type mismatch: account is {account.account_type.value}, "
                f"new parent is {new_parent.account_type.value}. "
                "Account and parent must have the same account type."
            )

        # Check for circular reference
        if self.detect_circular_reference(account_id, new_parent_id, organization_id):
            raise CircularReferenceException(
                "Cannot move account: this would create a circular reference in the hierarchy"
            )

        # Store old parent ID
        old_parent_id = account.parent_account_id

        # Update account's parent
        self.repo.update(account, {"parent_account_id": new_parent_id})

        # Update new parent to be non-posting account
        if new_parent.is_posting_account:
            self.repo.update(new_parent, {"is_posting_account": False})

        # If old parent has no more children, make it a posting account
        if old_parent_id and not self.repo.has_children(old_parent_id, organization_id):
            old_parent = self.repo.get_by_id(old_parent_id, organization_id)
            if old_parent:
                self.repo.update(old_parent, {"is_posting_account": True})

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
        # Validate account exists
        account = self.repo.get_by_id(account_id, organization_id)
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Account with ID {account_id} not found"
            )

        return self.repo.get_children(account_id, organization_id)

    def get_parent(
        self,
        account_id: UUID,
        organization_id: UUID,
    ) -> Account | None:
        """
        Get the parent account of an account.

        Args:
            account_id: Account UUID
            organization_id: Organization UUID

        Returns:
            Parent Account object or None if account is a root account

        Raises:
            ChartOfAccountNotFoundException: If account not found
        """
        # Validate account exists
        account = self.repo.get_by_id(account_id, organization_id)
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Account with ID {account_id} not found"
            )

        if not account.parent_account_id:
            return None

        return self.repo.get_by_id(account.parent_account_id, organization_id)

    def get_ancestors(
        self,
        account_id: UUID,
        organization_id: UUID,
        use_recursive_cte: bool = True,
    ) -> list[Account]:
        """
        Get all ancestor accounts from the account up to the root.

        Args:
            account_id: Account UUID
            organization_id: Organization UUID
            use_recursive_cte: Use recursive CTE for better performance (default: True)

        Returns:
            List of ancestor accounts ordered from immediate parent to root

        Raises:
            ChartOfAccountNotFoundException: If account not found
        """
        # Validate account exists
        account = self.repo.get_by_id(account_id, organization_id)
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Account with ID {account_id} not found"
            )

        # Use recursive CTE for better performance
        if use_recursive_cte:
            return self.repo.get_ancestors_recursive(account_id, organization_id)

        # Fallback to iterative approach
        ancestors = []
        current_id = account.parent_account_id

        # Traverse up the hierarchy
        visited = set()
        while current_id:
            # Prevent infinite loops
            if current_id in visited:
                break
            visited.add(current_id)

            parent = self.repo.get_by_id(current_id, organization_id)
            if not parent:
                break

            ancestors.append(parent)
            current_id = parent.parent_account_id

        return ancestors

    def get_descendants(
        self,
        account_id: UUID,
        organization_id: UUID,
        use_recursive_cte: bool = True,
    ) -> list[Account]:
        """
        Get all descendant accounts recursively.

        Args:
            account_id: Account UUID
            organization_id: Organization UUID
            use_recursive_cte: Use recursive CTE for better performance (default: True)

        Returns:
            List of all descendant accounts (children, grandchildren, etc.)

        Raises:
            ChartOfAccountNotFoundException: If account not found
        """
        # Validate account exists
        account = self.repo.get_by_id(account_id, organization_id)
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Account with ID {account_id} not found"
            )

        # Use recursive CTE for better performance
        if use_recursive_cte:
            return self.repo.get_descendants_recursive(account_id, organization_id)

        # Fallback to iterative approach
        descendants = []
        visited = set()

        def collect_descendants(parent_id: UUID) -> None:
            """Recursively collect all descendants"""
            # Prevent infinite loops
            if parent_id in visited:
                return
            visited.add(parent_id)

            children = self.repo.get_children(parent_id, organization_id)
            for child in children:
                descendants.append(child)
                collect_descendants(child.id)

        collect_descendants(account_id)
        return descendants

    def get_account_path(
        self,
        account_id: UUID,
        organization_id: UUID,
    ) -> list[str]:
        """
        Calculate the account path from root to the account.

        Args:
            account_id: Account UUID
            organization_id: Organization UUID

        Returns:
            List of account codes from root to the account

        Raises:
            ChartOfAccountNotFoundException: If account not found
        """
        # Validate account exists
        account = self.repo.get_by_id(account_id, organization_id)
        if not account:
            raise ChartOfAccountNotFoundException(
                f"Account with ID {account_id} not found"
            )

        # Get ancestors
        ancestors = self.get_ancestors(account_id, organization_id)

        # Build path from root to account (reverse ancestors list)
        path = [ancestor.account_code for ancestor in reversed(ancestors)]
        path.append(account.account_code)

        return path

    def detect_circular_reference(
        self,
        account_id: UUID,
        proposed_parent_id: UUID,
        organization_id: UUID,
    ) -> bool:
        """
        Detect if setting proposed_parent_id as parent would create a circular reference.

        Uses graph traversal to check if account_id appears in the ancestor chain
        of proposed_parent_id.

        Args:
            account_id: Account UUID that would become the child
            proposed_parent_id: Proposed parent account UUID
            organization_id: Organization UUID

        Returns:
            True if circular reference would be created, False otherwise
        """
        # If trying to set account as its own parent
        if account_id == proposed_parent_id:
            return True

        # Traverse up from proposed parent to check if account_id appears
        current_id = proposed_parent_id
        visited = set()

        while current_id:
            # Prevent infinite loops in case of existing circular references
            if current_id in visited:
                return True

            # If we find the account_id in the ancestor chain, it's circular
            if current_id == account_id:
                return True

            visited.add(current_id)

            # Get parent of current account
            current = self.repo.get_by_id(current_id, organization_id)
            if not current:
                break

            current_id = current.parent_account_id

        return False

    def validate_hierarchy(
        self,
        account_id: UUID,
        parent_id: UUID,
        organization_id: UUID,
    ) -> bool:
        """
        Validate if a parent-child relationship is valid.

        Checks:
        - Both accounts exist
        - No circular reference
        - Account types match

        Args:
            account_id: Child account UUID
            parent_id: Parent account UUID
            organization_id: Organization UUID

        Returns:
            True if hierarchy is valid, False otherwise
        """
        try:
            # Check if accounts exist
            account = self.repo.get_by_id(account_id, organization_id)
            parent = self.repo.get_by_id(parent_id, organization_id)

            if not account or not parent:
                return False

            # Check for circular reference
            if self.detect_circular_reference(account_id, parent_id, organization_id):
                return False

            # Check account type consistency
            if account.account_type != parent.account_type:
                return False

            return True

        except Exception:
            return False
