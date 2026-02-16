"""Unit tests for account status management service methods"""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ChartOfAccountNotFoundException, ValidationError
from app.models.base import AccountStatus, AccountType
from app.models.chart_of_account import Account
from app.services.chart_of_account_service import ChartOfAccountService


@pytest.fixture
def test_account(db_session):
    """Create a test account"""
    account = Account(
        account_code="TEST-001",
        account_name="Test Account",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        created_by="test_user",
        updated_by="test_user",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


class TestAccountStatusManagement:
    """Tests for account status management service methods"""

    def test_activate_account(self, db_session, test_account):
        """Test activating an account"""
        service = ChartOfAccountService(db_session)
        
        # First deactivate
        test_account.status = AccountStatus.INACTIVE
        db_session.commit()
        
        # Activate
        user_id = uuid.uuid4()
        result = service.activate_account(test_account.id, user_id)
        
        assert result.status == AccountStatus.ACTIVE
        assert result.id == test_account.id

    def test_deactivate_account(self, db_session, test_account):
        """Test deactivating an account"""
        service = ChartOfAccountService(db_session)
        
        user_id = uuid.uuid4()
        result = service.deactivate_account(test_account.id, user_id)
        
        assert result.status == AccountStatus.INACTIVE
        assert result.id == test_account.id

    def test_archive_account(self, db_session, test_account):
        """Test archiving an account"""
        service = ChartOfAccountService(db_session)
        
        user_id = uuid.uuid4()
        result = service.archive_account(test_account.id, user_id)
        
        assert result.status == AccountStatus.ARCHIVED
        assert result.id == test_account.id

    def test_activate_nonexistent_account(self, db_session):
        """Test activating a non-existent account raises exception"""
        service = ChartOfAccountService(db_session)
        
        fake_id = uuid.uuid4()
        with pytest.raises(ChartOfAccountNotFoundException):
            service.activate_account(fake_id)

    def test_deactivate_nonexistent_account(self, db_session):
        """Test deactivating a non-existent account raises exception"""
        service = ChartOfAccountService(db_session)
        
        fake_id = uuid.uuid4()
        with pytest.raises(ChartOfAccountNotFoundException):
            service.deactivate_account(fake_id)

    def test_archive_nonexistent_account(self, db_session):
        """Test archiving a non-existent account raises exception"""
        service = ChartOfAccountService(db_session)
        
        fake_id = uuid.uuid4()
        with pytest.raises(ChartOfAccountNotFoundException):
            service.archive_account(fake_id)

    def test_status_transitions(self, db_session, test_account):
        """Test multiple status transitions"""
        service = ChartOfAccountService(db_session)
        user_id = uuid.uuid4()
        
        # Start as active
        assert test_account.status == AccountStatus.ACTIVE
        
        # Deactivate
        result = service.deactivate_account(test_account.id, user_id)
        assert result.status == AccountStatus.INACTIVE
        
        # Reactivate
        result = service.activate_account(test_account.id, user_id)
        assert result.status == AccountStatus.ACTIVE
        
        # Archive
        result = service.archive_account(test_account.id, user_id)
        assert result.status == AccountStatus.ARCHIVED
        
        # Can reactivate from archived
        result = service.activate_account(test_account.id, user_id)
        assert result.status == AccountStatus.ACTIVE

    def test_validate_posting_account_active(self, db_session, test_account):
        """Test validating an active posting account succeeds"""
        service = ChartOfAccountService(db_session)
        
        # Should not raise exception
        service.validate_posting_account(test_account.id)

    def test_validate_posting_account_inactive(self, db_session, test_account):
        """Test validating an inactive account raises exception"""
        service = ChartOfAccountService(db_session)
        
        # Deactivate account
        test_account.status = AccountStatus.INACTIVE
        db_session.commit()
        
        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            service.validate_posting_account(test_account.id)
        
        assert "inactive" in str(exc_info.value).lower()

    def test_validate_posting_account_not_posting(self, db_session, test_account):
        """Test validating a non-posting account raises exception"""
        service = ChartOfAccountService(db_session)
        
        # Make account non-posting
        test_account.is_posting_account = False
        db_session.commit()
        
        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            service.validate_posting_account(test_account.id)
        
        assert "non-posting" in str(exc_info.value).lower()
