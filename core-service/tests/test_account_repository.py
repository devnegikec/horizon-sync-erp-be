"""Account repository tests"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.models.base import AccountStatus, AccountType
from app.repositories.chart_of_account_repository import AccountRepository


@pytest.fixture
def account_repo(db_session):
    """Create an account repository instance"""
    db_session.execute(text("PRAGMA foreign_keys = ON"))
    return AccountRepository(db_session)


@pytest.fixture
def test_account_data(mock_current_user):
    """Sample account data for testing"""
    return {
        "organization_id": mock_current_user.organization_id,
        "account_code": "1000-01",
        "account_name": "Cash Account",
        "account_type": AccountType.ASSET,
        "currency": "USD",
        "status": AccountStatus.ACTIVE,
        "is_posting_account": True,
        "description": "Main cash account",
        "created_by": str(mock_current_user.id),
        "updated_by": str(mock_current_user.id),
    }


class TestAccountRepositoryCreate:
    """Tests for AccountRepository.create"""

    def test_create_account_success(self, account_repo, test_account_data):
        """Test creating an account successfully"""
        account = account_repo.create(test_account_data)

        assert account.id is not None
        assert account.account_code == test_account_data["account_code"]
        assert account.account_name == test_account_data["account_name"]
        assert account.account_type == AccountType.ASSET
        assert account.status == AccountStatus.ACTIVE
        assert account.currency == "USD"
        assert account.is_posting_account is True
        assert account.created_at is not None
        assert account.updated_at is not None

    def test_create_account_duplicate_code(self, account_repo, test_account_data):
        """Test creating an account with duplicate code fails"""
        account_repo.create(test_account_data)

        # Try to create another account with same code
        duplicate_data = test_account_data.copy()
        duplicate_data["account_name"] = "Different Name"

        with pytest.raises(IntegrityError):
            account_repo.create(duplicate_data)

    def test_create_account_with_parent(self, account_repo, test_account_data):
        """Test creating an account with a parent account"""
        # Create parent account
        parent = account_repo.create(test_account_data)

        # Create child account
        child_data = test_account_data.copy()
        child_data["account_code"] = "1000-02"
        child_data["account_name"] = "Petty Cash"
        child_data["parent_account_id"] = parent.id

        child = account_repo.create(child_data)

        assert child.parent_account_id == parent.id
        assert child.parent_account.id == parent.id


class TestAccountRepositoryGetById:
    """Tests for AccountRepository.get_by_id"""

    def test_get_by_id_success(self, account_repo, test_account_data, mock_current_user):
        """Test getting an account by ID"""
        account = account_repo.create(test_account_data)

        retrieved = account_repo.get_by_id(account.id, mock_current_user.organization_id)

        assert retrieved is not None
        assert retrieved.id == account.id
        assert retrieved.account_code == test_account_data["account_code"]

    def test_get_by_id_not_found(self, account_repo, mock_current_user):
        """Test getting a non-existent account"""
        fake_id = uuid.uuid4()
        retrieved = account_repo.get_by_id(fake_id, mock_current_user.organization_id)

        assert retrieved is None


class TestAccountRepositoryGetByCode:
    """Tests for AccountRepository.get_by_code"""

    def test_get_by_code_success(self, account_repo, test_account_data, mock_current_user):
        """Test getting an account by code"""
        account = account_repo.create(test_account_data)

        retrieved = account_repo.get_by_code(test_account_data["account_code"], mock_current_user.organization_id)

        assert retrieved is not None
        assert retrieved.id == account.id
        assert retrieved.account_code == test_account_data["account_code"]

    def test_get_by_code_not_found(self, account_repo, mock_current_user):
        """Test getting a non-existent account by code"""
        retrieved = account_repo.get_by_code("NONEXISTENT", mock_current_user.organization_id)

        assert retrieved is None


class TestAccountRepositoryUpdate:
    """Tests for AccountRepository.update"""

    def test_update_account_success(self, account_repo, test_account_data):
        """Test updating an account"""
        account = account_repo.create(test_account_data)

        update_data = {
            "account_name": "Updated Cash Account",
            "description": "Updated description",
        }

        updated = account_repo.update(account, update_data)

        assert updated.account_name == "Updated Cash Account"
        assert updated.description == "Updated description"
        assert updated.account_code == test_account_data["account_code"]

    def test_update_account_status(self, account_repo, test_account_data):
        """Test updating account status"""
        account = account_repo.create(test_account_data)

        update_data = {"status": AccountStatus.INACTIVE}

        updated = account_repo.update(account, update_data)

        assert updated.status == AccountStatus.INACTIVE

    def test_update_account_duplicate_code(self, account_repo, test_account_data):
        """Test updating account code to duplicate fails"""
        account1 = account_repo.create(test_account_data)

        # Create second account
        account2_data = test_account_data.copy()
        account2_data["account_code"] = "1000-02"
        account2_data["account_name"] = "Bank Account"
        account2 = account_repo.create(account2_data)

        # Try to update account2 code to match account1
        update_data = {"account_code": account1.account_code}

        with pytest.raises(IntegrityError):
            account_repo.update(account2, update_data)


class TestAccountRepositoryDelete:
    """Tests for AccountRepository.delete"""

    def test_delete_account_success(self, account_repo, test_account_data, mock_current_user):
        """Test deleting an account"""
        account = account_repo.create(test_account_data)
        account_id = account.id

        account_repo.delete(account)

        # Verify it's deleted
        retrieved = account_repo.get_by_id(account_id, mock_current_user.organization_id)
        assert retrieved is None

    def test_delete_account_with_children_fails(self, account_repo, test_account_data):
        """Test deleting an account with children fails"""
        # Create parent account
        parent = account_repo.create(test_account_data)

        # Create child account
        child_data = test_account_data.copy()
        child_data["account_code"] = "1000-02"
        child_data["account_name"] = "Petty Cash"
        child_data["parent_account_id"] = parent.id
        account_repo.create(child_data)

        # Try to delete parent - should fail due to foreign key constraint
        with pytest.raises(IntegrityError):
            account_repo.delete(parent)


class TestAccountRepositoryListAll:
    """Tests for AccountRepository.list_all"""

    def test_list_all_empty(self, account_repo, mock_current_user):
        """Test listing accounts when none exist"""
        accounts = account_repo.list_all(organization_id=mock_current_user.organization_id)

        assert accounts == []

    def test_list_all_with_data(self, account_repo, test_account_data, mock_current_user):
        """Test listing accounts with data"""
        account_repo.create(test_account_data)

        accounts = account_repo.list_all(organization_id=mock_current_user.organization_id)

        assert len(accounts) == 1
        assert accounts[0].account_code == test_account_data["account_code"]

    def test_list_all_filter_by_type(self, account_repo, test_account_data, mock_current_user):
        """Test filtering accounts by type"""
        # Create asset account
        account_repo.create(test_account_data)

        # Create liability account
        liability_data = test_account_data.copy()
        liability_data["account_code"] = "2000-01"
        liability_data["account_name"] = "Accounts Payable"
        liability_data["account_type"] = AccountType.LIABILITY
        account_repo.create(liability_data)

        # Filter by asset type
        asset_accounts = account_repo.list_all(
            organization_id=mock_current_user.organization_id,
            account_type=AccountType.ASSET
        )

        assert len(asset_accounts) == 1
        assert asset_accounts[0].account_type == AccountType.ASSET

    def test_list_all_filter_by_status(self, account_repo, test_account_data, mock_current_user):
        """Test filtering accounts by status"""
        # Create active account
        account_repo.create(test_account_data)

        # Create inactive account
        inactive_data = test_account_data.copy()
        inactive_data["account_code"] = "1000-02"
        inactive_data["account_name"] = "Inactive Account"
        inactive_data["status"] = AccountStatus.INACTIVE
        account_repo.create(inactive_data)

        # Filter by active status
        active_accounts = account_repo.list_all(
            organization_id=mock_current_user.organization_id,
            status=AccountStatus.ACTIVE
        )

        assert len(active_accounts) == 1
        assert active_accounts[0].status == AccountStatus.ACTIVE

    def test_list_all_filter_by_parent(self, account_repo, test_account_data, mock_current_user):
        """Test filtering accounts by parent"""
        # Create parent account
        parent = account_repo.create(test_account_data)

        # Create child accounts
        for i in range(3):
            child_data = test_account_data.copy()
            child_data["account_code"] = f"1000-0{i+2}"
            child_data["account_name"] = f"Child Account {i+1}"
            child_data["parent_account_id"] = parent.id
            account_repo.create(child_data)

        # Filter by parent
        children = account_repo.list_all(
            organization_id=mock_current_user.organization_id,
            parent_account_id=parent.id
        )

        assert len(children) == 3

    def test_list_all_search(self, account_repo, test_account_data, mock_current_user):
        """Test searching accounts by code or name"""
        account_repo.create(test_account_data)

        # Create another account
        other_data = test_account_data.copy()
        other_data["account_code"] = "2000-01"
        other_data["account_name"] = "Bank Account"
        account_repo.create(other_data)

        # Search by code
        results = account_repo.list_all(
            organization_id=mock_current_user.organization_id,
            search="1000"
        )
        assert len(results) == 1
        assert results[0].account_code == "1000-01"

        # Search by name (case-insensitive)
        results = account_repo.list_all(
            organization_id=mock_current_user.organization_id,
            search="bank"
        )
        assert len(results) == 1
        assert results[0].account_name == "Bank Account"

    def test_list_all_sorting(self, account_repo, test_account_data, mock_current_user):
        """Test sorting accounts"""
        # Create multiple accounts
        codes = ["1000-03", "1000-01", "1000-02"]
        for code in codes:
            data = test_account_data.copy()
            data["account_code"] = code
            data["account_name"] = f"Account {code}"
            account_repo.create(data)

        # Test ascending order (default)
        accounts_asc = account_repo.list_all(
            organization_id=mock_current_user.organization_id,
            sort_by="account_code",
            sort_order="asc"
        )
        assert accounts_asc[0].account_code == "1000-01"
        assert accounts_asc[1].account_code == "1000-02"
        assert accounts_asc[2].account_code == "1000-03"

        # Test descending order
        accounts_desc = account_repo.list_all(
            organization_id=mock_current_user.organization_id,
            sort_by="account_code",
            sort_order="desc"
        )
        assert accounts_desc[0].account_code == "1000-03"
        assert accounts_desc[1].account_code == "1000-02"
        assert accounts_desc[2].account_code == "1000-01"


class TestAccountRepositoryHelperMethods:
    """Tests for helper methods"""

    def test_account_code_exists(self, account_repo, test_account_data, mock_current_user):
        """Test checking if account code exists"""
        account_repo.create(test_account_data)

        assert account_repo.account_code_exists(
            test_account_data["account_code"],
            mock_current_user.organization_id
        ) is True
        assert account_repo.account_code_exists(
            "NONEXISTENT",
            mock_current_user.organization_id
        ) is False

    def test_account_code_exists_exclude_id(self, account_repo, test_account_data, mock_current_user):
        """Test checking account code exists with exclusion"""
        account = account_repo.create(test_account_data)

        # Should return False when excluding the account's own ID
        assert account_repo.account_code_exists(
            test_account_data["account_code"],
            mock_current_user.organization_id,
            exclude_id=account.id
        ) is False

        # Should return True when not excluding
        assert account_repo.account_code_exists(
            test_account_data["account_code"],
            mock_current_user.organization_id
        ) is True

    def test_has_children(self, account_repo, test_account_data, mock_current_user):
        """Test checking if account has children"""
        # Create parent account
        parent = account_repo.create(test_account_data)

        assert account_repo.has_children(parent.id, mock_current_user.organization_id) is False

        # Create child account
        child_data = test_account_data.copy()
        child_data["account_code"] = "1000-02"
        child_data["account_name"] = "Child Account"
        child_data["parent_account_id"] = parent.id
        account_repo.create(child_data)

        assert account_repo.has_children(parent.id, mock_current_user.organization_id) is True

    def test_get_children(self, account_repo, test_account_data, mock_current_user):
        """Test getting child accounts"""
        # Create parent account
        parent = account_repo.create(test_account_data)

        # Create child accounts
        child_codes = ["1000-02", "1000-03", "1000-04"]
        for code in child_codes:
            child_data = test_account_data.copy()
            child_data["account_code"] = code
            child_data["account_name"] = f"Child {code}"
            child_data["parent_account_id"] = parent.id
            account_repo.create(child_data)

        children = account_repo.get_children(parent.id, mock_current_user.organization_id)

        assert len(children) == 3
        assert all(child.parent_account_id == parent.id for child in children)
        # Verify they're sorted by account_code
        assert children[0].account_code == "1000-02"
        assert children[1].account_code == "1000-03"
        assert children[2].account_code == "1000-04"

    def test_get_with_parent(self, account_repo, test_account_data, mock_current_user):
        """Test getting account with parent relationship loaded"""
        # Create parent account
        parent = account_repo.create(test_account_data)

        # Create child account
        child_data = test_account_data.copy()
        child_data["account_code"] = "1000-02"
        child_data["account_name"] = "Child Account"
        child_data["parent_account_id"] = parent.id
        child = account_repo.create(child_data)

        # Get child with parent loaded
        retrieved = account_repo.get_with_parent(child.id, mock_current_user.organization_id)

        assert retrieved is not None
        assert retrieved.id == child.id
        assert retrieved.parent_account is not None
        assert retrieved.parent_account.id == parent.id
        assert retrieved.parent_account.account_code == parent.account_code
