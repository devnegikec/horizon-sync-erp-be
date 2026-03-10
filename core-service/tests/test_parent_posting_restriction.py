"""Integration tests for parent account posting restriction (Requirement 2.3)"""

import uuid

import pytest
from fastapi import status

from app.models.base import AccountType
from app.models.chart_of_account import Account


@pytest.fixture
def test_organization_id():
    """Create a test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def test_user_id():
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


class TestParentAccountPostingRestriction:
    """Test parent account posting restriction (Requirement 2.3)"""

    def test_parent_becomes_non_posting_when_child_added(
        self, db_session, test_organization_id
    ):
        """Test that parent account becomes non-posting when a child is added"""
        from app.services.hierarchy_manager import HierarchyManager

        # Create parent account (initially posting)
        parent = create_account(
            db_session,
            test_organization_id,
            "1000",
            "Assets",
            is_posting_account=True,
        )
        assert parent.is_posting_account is True

        # Create child account
        child = create_account(
            db_session, test_organization_id, "1100", "Current Assets"
        )

        # Add child to parent
        hierarchy_manager = HierarchyManager(db_session)
        hierarchy_manager.add_child(parent.id, child.id, test_organization_id)

        # Verify parent is now non-posting
        db_session.refresh(parent)
        assert parent.is_posting_account is False

    def test_parent_remains_non_posting_with_multiple_children(
        self, db_session, test_organization_id
    ):
        """Test that parent remains non-posting when it has multiple children"""
        from app.services.hierarchy_manager import HierarchyManager

        # Create parent account
        parent = create_account(
            db_session, test_organization_id, "1000", "Assets", is_posting_account=False
        )

        # Create and add first child
        child1 = create_account(
            db_session, test_organization_id, "1100", "Current Assets"
        )
        hierarchy_manager = HierarchyManager(db_session)
        hierarchy_manager.add_child(parent.id, child1.id, test_organization_id)

        # Create and add second child
        child2 = create_account(
            db_session, test_organization_id, "1200", "Fixed Assets"
        )
        hierarchy_manager.add_child(parent.id, child2.id, test_organization_id)

        # Verify parent is still non-posting
        db_session.refresh(parent)
        assert parent.is_posting_account is False

    def test_parent_becomes_posting_when_last_child_removed(
        self, db_session, test_organization_id
    ):
        """Test that parent becomes posting when last child is removed"""
        from app.services.hierarchy_manager import HierarchyManager

        # Create parent with child
        parent = create_account(
            db_session, test_organization_id, "1000", "Assets", is_posting_account=False
        )
        child = create_account(
            db_session,
            test_organization_id,
            "1100",
            "Current Assets",
            parent_account_id=parent.id,
        )

        # Remove child
        hierarchy_manager = HierarchyManager(db_session)
        hierarchy_manager.remove_child(child.id, test_organization_id)

        # Verify parent is now posting
        db_session.refresh(parent)
        assert parent.is_posting_account is True

    def test_validate_posting_rejects_parent_account(
        self, db_session, test_organization_id
    ):
        """Test that validate_posting_account rejects parent accounts"""
        from app.core.exceptions import ValidationError
        from app.services.chart_of_account_service import ChartOfAccountService
        from app.services.hierarchy_manager import HierarchyManager

        # Create parent and child
        parent = create_account(
            db_session, test_organization_id, "1000", "Assets", is_posting_account=True
        )
        child = create_account(
            db_session, test_organization_id, "1100", "Current Assets"
        )

        # Add child to parent (makes parent non-posting)
        hierarchy_manager = HierarchyManager(db_session)
        hierarchy_manager.add_child(parent.id, child.id, test_organization_id)

        # Verify parent is non-posting
        db_session.refresh(parent)
        assert parent.is_posting_account is False

        # Validate posting should fail
        service = ChartOfAccountService(db_session)
        with pytest.raises(ValidationError) as exc_info:
            service.validate_posting_account(parent.id, test_organization_id)

        assert "non-posting" in str(exc_info.value).lower()
        assert "parent" in str(exc_info.value).lower()

    def test_validate_posting_accepts_leaf_account(
        self, db_session, test_organization_id
    ):
        """Test that validate_posting_account accepts leaf accounts"""
        from app.services.chart_of_account_service import ChartOfAccountService

        # Create leaf account (no children)
        account = create_account(
            db_session, test_organization_id, "1100", "Cash", is_posting_account=True
        )

        # Validate posting should succeed
        service = ChartOfAccountService(db_session)
        service.validate_posting_account(account.id, test_organization_id)
        # No exception means success

    def test_validate_posting_accepts_child_account(
        self, db_session, test_organization_id
    ):
        """Test that validate_posting_account accepts child accounts"""
        from app.services.chart_of_account_service import ChartOfAccountService
        from app.services.hierarchy_manager import HierarchyManager

        # Create parent and child
        parent = create_account(
            db_session, test_organization_id, "1000", "Assets", is_posting_account=True
        )
        child = create_account(
            db_session, test_organization_id, "1100", "Current Assets"
        )

        # Add child to parent
        hierarchy_manager = HierarchyManager(db_session)
        hierarchy_manager.add_child(parent.id, child.id, test_organization_id)

        # Child should still be posting
        db_session.refresh(child)
        assert child.is_posting_account is True

        # Validate posting on child should succeed
        service = ChartOfAccountService(db_session)
        service.validate_posting_account(child.id, test_organization_id)
        # No exception means success

    def test_moving_account_updates_parent_posting_status(
        self, db_session, test_organization_id
    ):
        """Test that moving an account updates both old and new parent posting status"""
        from app.services.hierarchy_manager import HierarchyManager

        # Create old parent with child
        old_parent = create_account(
            db_session, test_organization_id, "1000", "Assets", is_posting_account=False
        )
        account = create_account(
            db_session,
            test_organization_id,
            "1100",
            "Current Assets",
            parent_account_id=old_parent.id,
        )

        # Create new parent (initially posting)
        new_parent = create_account(
            db_session,
            test_organization_id,
            "1500",
            "Other Assets",
            is_posting_account=True,
        )

        # Move account to new parent
        hierarchy_manager = HierarchyManager(db_session)
        hierarchy_manager.move_account(account.id, new_parent.id, test_organization_id)

        # Verify old parent is now posting (no children)
        db_session.refresh(old_parent)
        assert old_parent.is_posting_account is True

        # Verify new parent is now non-posting (has child)
        db_session.refresh(new_parent)
        assert new_parent.is_posting_account is False


class TestValidatePostingAccountAPI:
    """Test the validate-posting API endpoint"""

    def test_validate_posting_api_accepts_valid_account(
        self, client, db_session, mock_current_user
    ):
        """Test that API accepts valid posting account"""
        # Create valid posting account
        account = create_account(
            db_session,
            mock_current_user.organization_id,
            "1100",
            "Cash",
            is_posting_account=True,
        )

        # Call API
        response = client.post(
            f"/api/v1/chart-of-accounts/{account.id}/validate-posting",
        )

        # Should return 204 No Content
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_validate_posting_api_rejects_parent_account(
        self, client, db_session, mock_current_user
    ):
        """Test that API rejects parent accounts"""
        from app.services.hierarchy_manager import HierarchyManager

        # Create parent and child
        parent = create_account(
            db_session,
            mock_current_user.organization_id,
            "1000",
            "Assets",
            is_posting_account=True,
        )
        child = create_account(
            db_session, mock_current_user.organization_id, "1100", "Current Assets"
        )

        # Add child to parent
        hierarchy_manager = HierarchyManager(db_session)
        hierarchy_manager.add_child(
            parent.id, child.id, mock_current_user.organization_id
        )

        # Call API
        response = client.post(
            f"/api/v1/chart-of-accounts/{parent.id}/validate-posting",
        )

        # Should return 400 Bad Request (ValidationError)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        # Check if error message contains "non-posting"
        error_message = str(response_data).lower()
        assert "non-posting" in error_message

    def test_validate_posting_api_rejects_inactive_account(
        self, client, db_session, mock_current_user
    ):
        """Test that API rejects inactive accounts"""
        from app.models.base import AccountStatus

        # Create inactive account
        account = create_account(
            db_session,
            mock_current_user.organization_id,
            "1100",
            "Cash",
            is_posting_account=True,
        )
        account.status = AccountStatus.INACTIVE
        db_session.commit()

        # Call API
        response = client.post(
            f"/api/v1/chart-of-accounts/{account.id}/validate-posting",
        )

        # Should return 400 Bad Request (ValidationError)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        # Check if error message contains "inactive"
        error_message = str(response_data).lower()
        assert "inactive" in error_message

    def test_validate_posting_api_rejects_nonexistent_account(
        self, client, mock_current_user
    ):
        """Test that API rejects nonexistent accounts"""
        fake_id = uuid.uuid4()

        # Call API
        response = client.post(
            f"/api/v1/chart-of-accounts/{fake_id}/validate-posting",
        )

        # Should return 404 Not Found
        assert response.status_code == status.HTTP_404_NOT_FOUND
