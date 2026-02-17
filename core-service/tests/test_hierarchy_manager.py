"""Tests for HierarchyManager service"""

import uuid

import pytest

from app.core.exceptions import (
    ChartOfAccountNotFoundException,
    CircularReferenceException,
    ValidationError,
)
from app.models.base import AccountType
from app.models.chart_of_account import Account
from app.services.hierarchy_manager import HierarchyManager


@pytest.fixture
def hierarchy_manager(db_session):
    """Create a hierarchy manager instance"""
    return HierarchyManager(db_session)


@pytest.fixture
def organization_id():
    """Create a test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Create a test user ID"""
    return uuid.uuid4()


def create_account(
    db_session,
    organization_id: uuid.UUID,
    account_code: str,
    account_name: str,
    account_type: AccountType = AccountType.ASSET,
    parent_account_id: uuid.UUID | None = None,
    is_posting_account: bool = True,
) -> Account:
    """Helper function to create an account"""
    account = Account(
        id=uuid.uuid4(),
        organization_id=organization_id,
        account_code=account_code,
        account_name=account_name,
        account_type=account_type,
        parent_account_id=parent_account_id,
        currency="USD",
        is_posting_account=is_posting_account,
        created_by="test_user",
        updated_by="test_user",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


class TestAddChild:
    """Test add_child method (Requirements 2.1, 2.4, 11.4)"""

    def test_add_child_establishes_relationship(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that adding a child establishes parent-child relationship"""
        # Create parent and child accounts
        parent = create_account(db_session, organization_id, "1000", "Assets")
        child = create_account(db_session, organization_id, "1100", "Current Assets")

        # Add child to parent
        hierarchy_manager.add_child(parent.id, child.id, organization_id)

        # Verify relationship
        db_session.refresh(child)
        assert child.parent_account_id == parent.id

    def test_add_child_makes_parent_non_posting(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that adding a child makes parent a non-posting account"""
        # Create parent and child accounts
        parent = create_account(
            db_session, organization_id, "1000", "Assets", is_posting_account=True
        )
        child = create_account(db_session, organization_id, "1100", "Current Assets")

        # Add child to parent
        hierarchy_manager.add_child(parent.id, child.id, organization_id)

        # Verify parent is now non-posting
        db_session.refresh(parent)
        assert parent.is_posting_account is False

    def test_add_child_rejects_type_mismatch(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that adding a child with different type is rejected"""
        # Create parent (asset) and child (liability)
        parent = create_account(
            db_session, organization_id, "1000", "Assets", AccountType.ASSET
        )
        child = create_account(
            db_session, organization_id, "2000", "Liabilities", AccountType.LIABILITY
        )

        # Attempt to add child should fail
        with pytest.raises(ValidationError) as exc_info:
            hierarchy_manager.add_child(parent.id, child.id, organization_id)

        assert "Account type mismatch" in str(exc_info.value)

    def test_add_child_rejects_circular_reference(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that circular references are rejected"""
        # Create parent and child
        parent = create_account(db_session, organization_id, "1000", "Assets")
        child = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=parent.id
        )

        # Attempt to make parent a child of child should fail
        with pytest.raises(CircularReferenceException):
            hierarchy_manager.add_child(child.id, parent.id, organization_id)

    def test_add_child_rejects_nonexistent_parent(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that adding child to nonexistent parent is rejected"""
        child = create_account(db_session, organization_id, "1100", "Current Assets")
        fake_parent_id = uuid.uuid4()

        with pytest.raises(ChartOfAccountNotFoundException):
            hierarchy_manager.add_child(fake_parent_id, child.id, organization_id)

    def test_add_child_rejects_nonexistent_child(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that adding nonexistent child is rejected"""
        parent = create_account(db_session, organization_id, "1000", "Assets")
        fake_child_id = uuid.uuid4()

        with pytest.raises(ChartOfAccountNotFoundException):
            hierarchy_manager.add_child(parent.id, fake_child_id, organization_id)


class TestRemoveChild:
    """Test remove_child method"""

    def test_remove_child_clears_parent_reference(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that removing a child clears its parent reference"""
        # Create parent and child
        parent = create_account(db_session, organization_id, "1000", "Assets")
        child = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=parent.id
        )

        # Remove child
        hierarchy_manager.remove_child(child.id, organization_id)

        # Verify parent reference is cleared
        db_session.refresh(child)
        assert child.parent_account_id is None

    def test_remove_child_makes_parent_posting_if_no_children(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that removing last child makes parent a posting account"""
        # Create parent and child
        parent = create_account(
            db_session, organization_id, "1000", "Assets", is_posting_account=False
        )
        child = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=parent.id
        )

        # Remove child
        hierarchy_manager.remove_child(child.id, organization_id)

        # Verify parent is now posting
        db_session.refresh(parent)
        assert parent.is_posting_account is True

    def test_remove_child_keeps_parent_non_posting_if_has_other_children(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that parent remains non-posting if it has other children"""
        # Create parent and two children
        parent = create_account(
            db_session, organization_id, "1000", "Assets", is_posting_account=False
        )
        child1 = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=parent.id
        )
        child2 = create_account(
            db_session, organization_id, "1200", "Fixed Assets", parent_account_id=parent.id
        )

        # Remove one child
        hierarchy_manager.remove_child(child1.id, organization_id)

        # Verify parent is still non-posting
        db_session.refresh(parent)
        assert parent.is_posting_account is False

    def test_remove_child_rejects_nonexistent_child(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that removing nonexistent child is rejected"""
        fake_child_id = uuid.uuid4()

        with pytest.raises(ChartOfAccountNotFoundException):
            hierarchy_manager.remove_child(fake_child_id, organization_id)


class TestMoveAccount:
    """Test move_account method (Requirements 2.4, 11.4)"""

    def test_move_account_updates_parent(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that moving an account updates its parent"""
        # Create accounts
        old_parent = create_account(db_session, organization_id, "1000", "Assets")
        new_parent = create_account(db_session, organization_id, "1500", "Other Assets")
        account = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=old_parent.id
        )

        # Move account
        hierarchy_manager.move_account(account.id, new_parent.id, organization_id)

        # Verify new parent
        db_session.refresh(account)
        assert account.parent_account_id == new_parent.id

    def test_move_account_updates_old_parent_posting_status(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that moving last child makes old parent a posting account"""
        # Create accounts
        old_parent = create_account(
            db_session, organization_id, "1000", "Assets", is_posting_account=False
        )
        new_parent = create_account(db_session, organization_id, "1500", "Other Assets")
        account = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=old_parent.id
        )

        # Move account
        hierarchy_manager.move_account(account.id, new_parent.id, organization_id)

        # Verify old parent is now posting
        db_session.refresh(old_parent)
        assert old_parent.is_posting_account is True

    def test_move_account_makes_new_parent_non_posting(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that moving account makes new parent non-posting"""
        # Create accounts
        old_parent = create_account(db_session, organization_id, "1000", "Assets")
        new_parent = create_account(
            db_session, organization_id, "1500", "Other Assets", is_posting_account=True
        )
        account = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=old_parent.id
        )

        # Move account
        hierarchy_manager.move_account(account.id, new_parent.id, organization_id)

        # Verify new parent is now non-posting
        db_session.refresh(new_parent)
        assert new_parent.is_posting_account is False

    def test_move_account_rejects_type_mismatch(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that moving to parent with different type is rejected"""
        # Create accounts
        old_parent = create_account(
            db_session, organization_id, "1000", "Assets", AccountType.ASSET
        )
        new_parent = create_account(
            db_session, organization_id, "2000", "Liabilities", AccountType.LIABILITY
        )
        account = create_account(
            db_session,
            organization_id,
            "1100",
            "Current Assets",
            AccountType.ASSET,
            parent_account_id=old_parent.id,
        )

        # Attempt to move should fail
        with pytest.raises(ValidationError) as exc_info:
            hierarchy_manager.move_account(account.id, new_parent.id, organization_id)

        assert "Account type mismatch" in str(exc_info.value)

    def test_move_account_rejects_circular_reference(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that circular references are rejected when moving"""
        # Create hierarchy: grandparent -> parent -> child
        grandparent = create_account(db_session, organization_id, "1000", "Assets")
        parent = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=grandparent.id
        )
        child = create_account(
            db_session, organization_id, "1110", "Cash", parent_account_id=parent.id
        )

        # Attempt to move grandparent under child should fail
        with pytest.raises(CircularReferenceException):
            hierarchy_manager.move_account(grandparent.id, child.id, organization_id)


class TestGetChildren:
    """Test get_children method"""

    def test_get_children_returns_direct_children(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_children returns only direct children"""
        # Create hierarchy
        parent = create_account(db_session, organization_id, "1000", "Assets")
        child1 = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=parent.id
        )
        child2 = create_account(
            db_session, organization_id, "1200", "Fixed Assets", parent_account_id=parent.id
        )
        grandchild = create_account(
            db_session, organization_id, "1110", "Cash", parent_account_id=child1.id
        )

        # Get children
        children = hierarchy_manager.get_children(parent.id, organization_id)

        # Verify only direct children are returned
        assert len(children) == 2
        child_ids = {c.id for c in children}
        assert child1.id in child_ids
        assert child2.id in child_ids
        assert grandchild.id not in child_ids

    def test_get_children_returns_empty_for_leaf_account(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_children returns empty list for leaf account"""
        # Create leaf account
        account = create_account(db_session, organization_id, "1000", "Cash")

        # Get children
        children = hierarchy_manager.get_children(account.id, organization_id)

        # Verify empty list
        assert len(children) == 0

    def test_get_children_rejects_nonexistent_account(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_children rejects nonexistent account"""
        fake_account_id = uuid.uuid4()

        with pytest.raises(ChartOfAccountNotFoundException):
            hierarchy_manager.get_children(fake_account_id, organization_id)


class TestGetParent:
    """Test get_parent method"""

    def test_get_parent_returns_parent_account(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_parent returns the parent account"""
        # Create parent and child
        parent = create_account(db_session, organization_id, "1000", "Assets")
        child = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=parent.id
        )

        # Get parent
        result = hierarchy_manager.get_parent(child.id, organization_id)

        # Verify parent
        assert result is not None
        assert result.id == parent.id

    def test_get_parent_returns_none_for_root_account(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_parent returns None for root account"""
        # Create root account
        account = create_account(db_session, organization_id, "1000", "Assets")

        # Get parent
        result = hierarchy_manager.get_parent(account.id, organization_id)

        # Verify None
        assert result is None

    def test_get_parent_rejects_nonexistent_account(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_parent rejects nonexistent account"""
        fake_account_id = uuid.uuid4()

        with pytest.raises(ChartOfAccountNotFoundException):
            hierarchy_manager.get_parent(fake_account_id, organization_id)


class TestGetAncestors:
    """Test get_ancestors method (Requirements 2.2)"""

    def test_get_ancestors_returns_all_ancestors(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_ancestors returns all ancestors from parent to root"""
        # Create hierarchy: root -> parent -> child
        root = create_account(db_session, organization_id, "1000", "Assets")
        parent = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=root.id
        )
        child = create_account(
            db_session, organization_id, "1110", "Cash", parent_account_id=parent.id
        )

        # Get ancestors
        ancestors = hierarchy_manager.get_ancestors(child.id, organization_id)

        # Verify ancestors (should be ordered from immediate parent to root)
        assert len(ancestors) == 2
        assert ancestors[0].id == parent.id
        assert ancestors[1].id == root.id

    def test_get_ancestors_returns_empty_for_root_account(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_ancestors returns empty list for root account"""
        # Create root account
        account = create_account(db_session, organization_id, "1000", "Assets")

        # Get ancestors
        ancestors = hierarchy_manager.get_ancestors(account.id, organization_id)

        # Verify empty list
        assert len(ancestors) == 0

    def test_get_ancestors_rejects_nonexistent_account(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_ancestors rejects nonexistent account"""
        fake_account_id = uuid.uuid4()

        with pytest.raises(ChartOfAccountNotFoundException):
            hierarchy_manager.get_ancestors(fake_account_id, organization_id)


class TestGetDescendants:
    """Test get_descendants method"""

    def test_get_descendants_returns_all_descendants(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_descendants returns all descendants recursively"""
        # Create hierarchy
        root = create_account(db_session, organization_id, "1000", "Assets")
        child1 = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=root.id
        )
        child2 = create_account(
            db_session, organization_id, "1200", "Fixed Assets", parent_account_id=root.id
        )
        grandchild1 = create_account(
            db_session, organization_id, "1110", "Cash", parent_account_id=child1.id
        )
        grandchild2 = create_account(
            db_session, organization_id, "1120", "Bank", parent_account_id=child1.id
        )

        # Get descendants
        descendants = hierarchy_manager.get_descendants(root.id, organization_id)

        # Verify all descendants are returned
        assert len(descendants) == 4
        descendant_ids = {d.id for d in descendants}
        assert child1.id in descendant_ids
        assert child2.id in descendant_ids
        assert grandchild1.id in descendant_ids
        assert grandchild2.id in descendant_ids

    def test_get_descendants_returns_empty_for_leaf_account(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_descendants returns empty list for leaf account"""
        # Create leaf account
        account = create_account(db_session, organization_id, "1000", "Cash")

        # Get descendants
        descendants = hierarchy_manager.get_descendants(account.id, organization_id)

        # Verify empty list
        assert len(descendants) == 0

    def test_get_descendants_rejects_nonexistent_account(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_descendants rejects nonexistent account"""
        fake_account_id = uuid.uuid4()

        with pytest.raises(ChartOfAccountNotFoundException):
            hierarchy_manager.get_descendants(fake_account_id, organization_id)


class TestGetAccountPath:
    """Test get_account_path method (Requirements 2.2)"""

    def test_get_account_path_returns_full_path(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_account_path returns full path from root to account"""
        # Create hierarchy: root -> parent -> child
        root = create_account(db_session, organization_id, "1000", "Assets")
        parent = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=root.id
        )
        child = create_account(
            db_session, organization_id, "1110", "Cash", parent_account_id=parent.id
        )

        # Get path
        path = hierarchy_manager.get_account_path(child.id, organization_id)

        # Verify path (should be ordered from root to account)
        assert len(path) == 3
        assert path[0] == root.account_code
        assert path[1] == parent.account_code
        assert path[2] == child.account_code

    def test_get_account_path_returns_single_code_for_root(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_account_path returns single code for root account"""
        # Create root account
        account = create_account(db_session, organization_id, "1000", "Assets")

        # Get path
        path = hierarchy_manager.get_account_path(account.id, organization_id)

        # Verify path
        assert len(path) == 1
        assert path[0] == account.account_code

    def test_get_account_path_rejects_nonexistent_account(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that get_account_path rejects nonexistent account"""
        fake_account_id = uuid.uuid4()

        with pytest.raises(ChartOfAccountNotFoundException):
            hierarchy_manager.get_account_path(fake_account_id, organization_id)


class TestDetectCircularReference:
    """Test detect_circular_reference method (Requirements 11.4)"""

    def test_detect_circular_reference_self_parent(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that self-parent is detected as circular"""
        # Create account
        account = create_account(db_session, organization_id, "1000", "Assets")

        # Check circular reference
        is_circular = hierarchy_manager.detect_circular_reference(
            account.id, account.id, organization_id
        )

        # Verify circular
        assert is_circular is True

    def test_detect_circular_reference_direct_cycle(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that direct cycle is detected"""
        # Create parent and child
        parent = create_account(db_session, organization_id, "1000", "Assets")
        child = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=parent.id
        )

        # Check if making parent a child of child would be circular
        is_circular = hierarchy_manager.detect_circular_reference(
            parent.id, child.id, organization_id
        )

        # Verify circular
        assert is_circular is True

    def test_detect_circular_reference_indirect_cycle(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that indirect cycle is detected"""
        # Create hierarchy: root -> parent -> child
        root = create_account(db_session, organization_id, "1000", "Assets")
        parent = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=root.id
        )
        child = create_account(
            db_session, organization_id, "1110", "Cash", parent_account_id=parent.id
        )

        # Check if making root a child of child would be circular
        is_circular = hierarchy_manager.detect_circular_reference(
            root.id, child.id, organization_id
        )

        # Verify circular
        assert is_circular is True

    def test_detect_circular_reference_valid_hierarchy(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that valid hierarchy is not detected as circular"""
        # Create accounts
        parent = create_account(db_session, organization_id, "1000", "Assets")
        child = create_account(db_session, organization_id, "1100", "Current Assets")

        # Check if making child a child of parent would be circular
        is_circular = hierarchy_manager.detect_circular_reference(
            child.id, parent.id, organization_id
        )

        # Verify not circular
        assert is_circular is False


class TestValidateHierarchy:
    """Test validate_hierarchy method"""

    def test_validate_hierarchy_valid_relationship(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that valid hierarchy is validated"""
        # Create accounts with same type
        parent = create_account(
            db_session, organization_id, "1000", "Assets", AccountType.ASSET
        )
        child = create_account(
            db_session, organization_id, "1100", "Current Assets", AccountType.ASSET
        )

        # Validate hierarchy
        is_valid = hierarchy_manager.validate_hierarchy(child.id, parent.id, organization_id)

        # Verify valid
        assert is_valid is True

    def test_validate_hierarchy_type_mismatch(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that type mismatch is invalid"""
        # Create accounts with different types
        parent = create_account(
            db_session, organization_id, "1000", "Assets", AccountType.ASSET
        )
        child = create_account(
            db_session, organization_id, "2000", "Liabilities", AccountType.LIABILITY
        )

        # Validate hierarchy
        is_valid = hierarchy_manager.validate_hierarchy(child.id, parent.id, organization_id)

        # Verify invalid
        assert is_valid is False

    def test_validate_hierarchy_circular_reference(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that circular reference is invalid"""
        # Create parent and child
        parent = create_account(db_session, organization_id, "1000", "Assets")
        child = create_account(
            db_session, organization_id, "1100", "Current Assets", parent_account_id=parent.id
        )

        # Validate hierarchy (parent as child of child)
        is_valid = hierarchy_manager.validate_hierarchy(parent.id, child.id, organization_id)

        # Verify invalid
        assert is_valid is False

    def test_validate_hierarchy_nonexistent_account(
        self, hierarchy_manager, db_session, organization_id
    ):
        """Test that nonexistent account is invalid"""
        # Create one account
        parent = create_account(db_session, organization_id, "1000", "Assets")
        fake_child_id = uuid.uuid4()

        # Validate hierarchy
        is_valid = hierarchy_manager.validate_hierarchy(fake_child_id, parent.id, organization_id)

        # Verify invalid
        assert is_valid is False
