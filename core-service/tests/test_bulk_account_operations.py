"""Tests for bulk account operations"""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.base import AccountStatus, AccountType
from app.models.chart_of_account import Account
from app.services.chart_of_account_service import ChartOfAccountService


@pytest.fixture
def sample_accounts(db_session: Session):
    """Create sample accounts for testing"""
    org_id = uuid4()
    user_id = uuid4()

    accounts = []
    for i in range(5):
        account = Account(
            organization_id=org_id,
            account_code=f"TEST-{i:03d}",
            account_name=f"Test Account {i}",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE if i < 3 else AccountStatus.INACTIVE,
            is_posting_account=True,
            created_by=str(user_id),
            updated_by=str(user_id),
        )
        db_session.add(account)
        accounts.append(account)

    db_session.commit()

    for account in accounts:
        db_session.refresh(account)

    return accounts, org_id, user_id


class TestBulkActivateAccounts:
    """Test bulk account activation"""

    def test_bulk_activate_success(self, db_session: Session, sample_accounts):
        """Test successful bulk activation"""
        accounts, org_id, user_id = sample_accounts
        service = ChartOfAccountService(db_session)

        # Get inactive account IDs
        inactive_ids = [a.id for a in accounts if a.status == AccountStatus.INACTIVE]

        result = service.bulk_activate_accounts(
            account_ids=inactive_ids,
            organization_id=org_id,
            user_id=user_id,
        )

        assert result["success_count"] == len(inactive_ids)
        assert result["failed_count"] == 0
        assert len(result["errors"]) == 0
        assert len(result["updated_ids"]) == len(inactive_ids)

        # Verify accounts are activated
        for account_id in inactive_ids:
            account = db_session.query(Account).filter(Account.id == account_id).first()
            assert account.status == AccountStatus.ACTIVE

    def test_bulk_activate_nonexistent_account(
        self, db_session: Session, sample_accounts
    ):
        """Test bulk activation with non-existent account"""
        accounts, org_id, user_id = sample_accounts
        service = ChartOfAccountService(db_session)

        # Include a non-existent account ID
        account_ids = [accounts[0].id, uuid4()]

        result = service.bulk_activate_accounts(
            account_ids=account_ids,
            organization_id=org_id,
            user_id=user_id,
        )

        assert result["success_count"] == 1
        assert result["failed_count"] == 1
        assert len(result["errors"]) == 1

    def test_bulk_activate_empty_list(self, db_session: Session, sample_accounts):
        """Test bulk activation with empty list"""
        _, org_id, user_id = sample_accounts
        service = ChartOfAccountService(db_session)

        result = service.bulk_activate_accounts(
            account_ids=[],
            organization_id=org_id,
            user_id=user_id,
        )

        assert result["success_count"] == 0
        assert result["failed_count"] == 0


class TestBulkDeactivateAccounts:
    """Test bulk account deactivation"""

    def test_bulk_deactivate_success(self, db_session: Session, sample_accounts):
        """Test successful bulk deactivation"""
        accounts, org_id, user_id = sample_accounts
        service = ChartOfAccountService(db_session)

        # Get active account IDs
        active_ids = [a.id for a in accounts if a.status == AccountStatus.ACTIVE]

        result = service.bulk_deactivate_accounts(
            account_ids=active_ids,
            organization_id=org_id,
            user_id=user_id,
        )

        assert result["success_count"] == len(active_ids)
        assert result["failed_count"] == 0
        assert len(result["errors"]) == 0
        assert len(result["updated_ids"]) == len(active_ids)

        # Verify accounts are deactivated
        for account_id in active_ids:
            account = db_session.query(Account).filter(Account.id == account_id).first()
            assert account.status == AccountStatus.INACTIVE

    def test_bulk_deactivate_mixed_results(self, db_session: Session, sample_accounts):
        """Test bulk deactivation with mixed results"""
        accounts, org_id, user_id = sample_accounts
        service = ChartOfAccountService(db_session)

        # Mix of valid and invalid IDs
        account_ids = [accounts[0].id, uuid4(), accounts[1].id]

        result = service.bulk_deactivate_accounts(
            account_ids=account_ids,
            organization_id=org_id,
            user_id=user_id,
        )

        assert result["success_count"] == 2
        assert result["failed_count"] == 1


class TestBulkDeleteAccounts:
    """Test bulk account deletion"""

    def test_bulk_delete_success(self, db_session: Session, sample_accounts):
        """Test successful bulk deletion"""
        accounts, org_id, user_id = sample_accounts
        service = ChartOfAccountService(db_session)

        # Delete first two accounts
        account_ids = [accounts[0].id, accounts[1].id]

        result = service.bulk_delete_accounts(
            account_ids=account_ids,
            organization_id=org_id,
            user_id=user_id,
        )

        assert result["success_count"] == 2
        assert result["failed_count"] == 0
        assert len(result["deleted_ids"]) == 2

        # Verify accounts are deleted
        for account_id in account_ids:
            account = db_session.query(Account).filter(Account.id == account_id).first()
            assert account is None

    def test_bulk_delete_with_children(self, db_session: Session):
        """Test bulk deletion with accounts that have children"""
        org_id = uuid4()
        user_id = uuid4()
        service = ChartOfAccountService(db_session)

        # Create parent account
        parent = Account(
            organization_id=org_id,
            account_code="PARENT-001",
            account_name="Parent Account",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=False,
            created_by=str(user_id),
            updated_by=str(user_id),
        )
        db_session.add(parent)
        db_session.commit()
        db_session.refresh(parent)

        # Create child account
        child = Account(
            organization_id=org_id,
            account_code="CHILD-001",
            account_name="Child Account",
            account_type=AccountType.ASSET,
            parent_account_id=parent.id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by=str(user_id),
            updated_by=str(user_id),
        )
        db_session.add(child)
        db_session.commit()

        # Try to delete parent without force
        result = service.bulk_delete_accounts(
            account_ids=[parent.id],
            organization_id=org_id,
            user_id=user_id,
            force=False,
        )

        assert result["success_count"] == 0
        assert result["failed_count"] == 1
        assert len(result["errors"]) == 1
        assert "child accounts" in result["errors"][0]["error"].lower()

    def test_bulk_delete_with_force(self, db_session: Session):
        """Test bulk deletion with force flag"""
        org_id = uuid4()
        user_id = uuid4()
        service = ChartOfAccountService(db_session)

        # Create parent account
        parent = Account(
            organization_id=org_id,
            account_code="PARENT-002",
            account_name="Parent Account 2",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=False,
            created_by=str(user_id),
            updated_by=str(user_id),
        )
        db_session.add(parent)
        db_session.commit()
        db_session.refresh(parent)

        # Create child account
        child = Account(
            organization_id=org_id,
            account_code="CHILD-002",
            account_name="Child Account 2",
            account_type=AccountType.ASSET,
            parent_account_id=parent.id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by=str(user_id),
            updated_by=str(user_id),
        )
        db_session.add(child)
        db_session.commit()

        # Delete parent with force
        result = service.bulk_delete_accounts(
            account_ids=[parent.id],
            organization_id=org_id,
            user_id=user_id,
            force=True,
        )

        assert result["success_count"] == 1
        assert result["failed_count"] == 0

    def test_bulk_delete_nonexistent_account(
        self, db_session: Session, sample_accounts
    ):
        """Test bulk deletion with non-existent account"""
        accounts, org_id, user_id = sample_accounts
        service = ChartOfAccountService(db_session)

        # Include a non-existent account ID
        account_ids = [accounts[0].id, uuid4()]

        result = service.bulk_delete_accounts(
            account_ids=account_ids,
            organization_id=org_id,
            user_id=user_id,
        )

        assert result["success_count"] == 1
        assert result["failed_count"] == 1
        assert len(result["errors"]) == 1
        assert "not found" in result["errors"][0]["error"].lower()
