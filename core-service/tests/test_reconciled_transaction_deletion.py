"""Test reconciled transaction deletion prevention"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4
from sqlalchemy.orm import Session

from app.services.bank_account_service import BankAccountService
from app.models.bank_account import BankAccount
from app.models.bank_transaction import BankTransaction
from app.core.exceptions import ReconciledTransactionDeletionException


class TestReconciledTransactionDeletion:
    """Test deletion prevention for reconciled transactions"""
    
    def test_delete_bank_account_with_reconciled_transactions_raises_exception(self):
        """Test that deleting a bank account with reconciled transactions raises an exception"""
        
        # Setup mock database session
        mock_db = Mock(spec=Session)
        
        # Create mock bank account
        bank_account_id = uuid4()
        organization_id = uuid4()
        mock_bank_account = Mock(spec=BankAccount)
        mock_bank_account.id = bank_account_id
        mock_bank_account.organization_id = organization_id
        mock_bank_account.bank_name = "Test Bank"
        mock_bank_account.account_holder_name = "Test Holder"
        mock_bank_account.currency = "USD"
        mock_bank_account.country_code = "US"
        mock_bank_account.is_active = True
        mock_bank_account.is_primary = False
        
        # Mock the query chain for get_bank_account_by_id
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # First query returns the bank account
        # Second query returns count of reconciled transactions
        mock_query.first.return_value = mock_bank_account
        mock_query.scalar.return_value = 3  # 3 reconciled transactions
        
        # Create service
        service = BankAccountService(mock_db)
        
        # Attempt to delete should raise exception
        with pytest.raises(ReconciledTransactionDeletionException) as exc_info:
            service.delete_bank_account(
                bank_account_id=bank_account_id,
                organization_id=organization_id,
                current_user="test_user"
            )
        
        # Verify exception message
        assert "Cannot delete bank account" in str(exc_info.value)
        assert "3 reconciled transaction(s)" in str(exc_info.value)
        assert "data integrity" in str(exc_info.value)
        
        # Verify delete was NOT called
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()
    
    def test_delete_bank_account_without_reconciled_transactions_succeeds(self):
        """Test that deleting a bank account without reconciled transactions succeeds"""
        
        # Setup mock database session
        mock_db = Mock(spec=Session)
        
        # Create mock bank account
        bank_account_id = uuid4()
        organization_id = uuid4()
        gl_account_id = uuid4()
        
        mock_gl_account = Mock()
        mock_gl_account.id = gl_account_id
        mock_gl_account.account_code = "1000"
        mock_gl_account.account_name = "Test GL Account"
        
        mock_bank_account = Mock(spec=BankAccount)
        mock_bank_account.id = bank_account_id
        mock_bank_account.organization_id = organization_id
        mock_bank_account.gl_account_id = gl_account_id
        mock_bank_account.gl_account = mock_gl_account
        mock_bank_account.bank_name = "Test Bank"
        mock_bank_account.account_holder_name = "Test Holder"
        mock_bank_account.currency = "USD"
        mock_bank_account.country_code = "US"
        mock_bank_account.is_active = True
        mock_bank_account.is_primary = False
        
        # Mock the query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # First query returns the bank account
        # Second query returns count of 0 reconciled transactions
        mock_query.first.return_value = mock_bank_account
        mock_query.scalar.return_value = 0  # No reconciled transactions
        
        # Create service
        service = BankAccountService(mock_db)
        
        # Delete should succeed
        service.delete_bank_account(
            bank_account_id=bank_account_id,
            organization_id=organization_id,
            current_user="test_user"
        )
        
        # Verify delete was called
        mock_db.delete.assert_called_once_with(mock_bank_account)
        mock_db.commit.assert_called_once()
    
    def test_delete_bank_account_with_unreconciled_transactions_succeeds(self):
        """Test that deleting a bank account with only unreconciled transactions succeeds"""
        
        # Setup mock database session
        mock_db = Mock(spec=Session)
        
        # Create mock bank account
        bank_account_id = uuid4()
        organization_id = uuid4()
        gl_account_id = uuid4()
        
        mock_gl_account = Mock()
        mock_gl_account.id = gl_account_id
        mock_gl_account.account_code = "1000"
        mock_gl_account.account_name = "Test GL Account"
        
        mock_bank_account = Mock(spec=BankAccount)
        mock_bank_account.id = bank_account_id
        mock_bank_account.organization_id = organization_id
        mock_bank_account.gl_account_id = gl_account_id
        mock_bank_account.gl_account = mock_gl_account
        mock_bank_account.bank_name = "Test Bank"
        mock_bank_account.account_holder_name = "Test Holder"
        mock_bank_account.currency = "USD"
        mock_bank_account.country_code = "US"
        mock_bank_account.is_active = True
        mock_bank_account.is_primary = False
        
        # Mock the query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # First query returns the bank account
        # Second query returns count of 0 reconciled transactions (but may have pending/cleared)
        mock_query.first.return_value = mock_bank_account
        mock_query.scalar.return_value = 0  # No reconciled transactions
        
        # Create service
        service = BankAccountService(mock_db)
        
        # Delete should succeed even with unreconciled transactions
        service.delete_bank_account(
            bank_account_id=bank_account_id,
            organization_id=organization_id,
            current_user="test_user"
        )
        
        # Verify delete was called
        mock_db.delete.assert_called_once_with(mock_bank_account)
        mock_db.commit.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
