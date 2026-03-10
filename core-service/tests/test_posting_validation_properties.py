"""
Property-based tests for transaction posting validation.

Tests universal properties that should hold across all valid inputs.
Feature: erp-chart-of-accounts
"""
import uuid
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from sqlalchemy.orm import Session

from app.models.chart_of_account import Account
from app.models.base import AccountType, AccountStatus
from app.services.chart_of_account_service import ChartOfAccountService
from app.core.exceptions import ChartOfAccountNotFoundException, ValidationError


# Custom strategies for generating test data
@st.composite
def account_data(draw):
    """Generate valid account data for testing."""
    account_types = [t.value for t in AccountType]
    account_statuses = [s.value for s in AccountStatus]
    
    return {
        "account_code": draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Nd'), min_codepoint=48, max_codepoint=90),
            min_size=4,
            max_size=20
        )),
        "account_name": draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs')),
            min_size=3,
            max_size=50
        )),
        "account_type": draw(st.sampled_from(account_types)),
        "status": draw(st.sampled_from(account_statuses)),
        "is_posting_account": draw(st.booleans()),
        "currency": draw(st.sampled_from(["USD", "EUR", "GBP", "JPY"])),
    }


class TestPostingValidationProperties:
    """Property-based test suite for transaction posting validation."""
    
    @settings(
        max_examples=5,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(data=account_data())
    def test_property_24_transaction_posting_validation(self, db_session: Session, data: dict):
        """
        Feature: erp-chart-of-accounts, Property 24: Transaction posting validation
        
        For any transaction posting request from external modules, if the target 
        account does not exist or is not active, the posting should be rejected.
        
        Validates: Requirements 8.3
        """
        # Arrange: Create organization ID
        organization_id = uuid.uuid4()
        
        # Skip if account code or name is empty after stripping
        assume(data["account_code"].strip() != "")
        assume(data["account_name"].strip() != "")
        
        # Create account in database
        account = Account(
            id=uuid.uuid4(),
            account_code=data["account_code"],
            account_name=data["account_name"],
            account_type=AccountType(data["account_type"]),
            status=AccountStatus(data["status"]),
            is_posting_account=data["is_posting_account"],
            currency=data["currency"],
            organization_id=organization_id,
            created_by="test_user",
            updated_by="test_user",
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        
        # Act & Assert
        service = ChartOfAccountService(db_session)
        
        # Property 1: If account is ACTIVE and is_posting_account=True, validation should succeed
        if account.status == AccountStatus.ACTIVE and account.is_posting_account:
            # Should not raise any exception
            service.validate_posting_account(account.id, organization_id)
        
        # Property 2: If account is not ACTIVE, validation should fail with descriptive error
        elif account.status != AccountStatus.ACTIVE:
            with pytest.raises(ValidationError) as exc_info:
                service.validate_posting_account(account.id, organization_id)
            
            # Error message should mention "inactive" and include account code
            error_msg = str(exc_info.value).lower()
            assert "inactive" in error_msg or "status" in error_msg
            assert account.account_code in str(exc_info.value)
        
        # Property 3: If account is not a posting account, validation should fail with descriptive error
        elif not account.is_posting_account:
            with pytest.raises(ValidationError) as exc_info:
                service.validate_posting_account(account.id, organization_id)
            
            # Error message should mention "non-posting" or "parent" and include account code
            error_msg = str(exc_info.value).lower()
            assert ("non-posting" in error_msg or "parent" in error_msg)
            assert account.account_code in str(exc_info.value)
    
    def test_property_24_nonexistent_account_rejection(self, db_session: Session):
        """
        Feature: erp-chart-of-accounts, Property 24: Transaction posting validation (nonexistent account)
        
        For any nonexistent account ID, validation should fail with appropriate error.
        
        Validates: Requirements 8.3
        """
        # Arrange
        organization_id = uuid.uuid4()
        nonexistent_account_id = uuid.uuid4()
        service = ChartOfAccountService(db_session)
        
        # Act & Assert: Validation should fail for nonexistent account
        with pytest.raises(ChartOfAccountNotFoundException) as exc_info:
            service.validate_posting_account(nonexistent_account_id, organization_id)
        
        # Error message should indicate account not found
        error_msg = str(exc_info.value).lower()
        assert "not found" in error_msg
        assert str(nonexistent_account_id) in str(exc_info.value)
    
    @settings(
        max_examples=5,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(data=account_data())
    def test_property_24_descriptive_error_messages(self, db_session: Session, data: dict):
        """
        Feature: erp-chart-of-accounts, Property 24: Transaction posting validation (error messages)
        
        For any validation failure, the error message should be descriptive and include
        the account code to help identify the problematic account.
        
        Validates: Requirements 8.3
        """
        # Arrange: Create organization ID
        organization_id = uuid.uuid4()
        
        # Skip if account code or name is empty after stripping
        assume(data["account_code"].strip() != "")
        assume(data["account_name"].strip() != "")
        
        # Force account to be invalid for posting (either inactive or non-posting)
        data["status"] = AccountStatus.INACTIVE.value
        
        # Create account in database
        account = Account(
            id=uuid.uuid4(),
            account_code=data["account_code"],
            account_name=data["account_name"],
            account_type=AccountType(data["account_type"]),
            status=AccountStatus(data["status"]),
            is_posting_account=data["is_posting_account"],
            currency=data["currency"],
            organization_id=organization_id,
            created_by="test_user",
            updated_by="test_user",
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        
        # Act & Assert
        service = ChartOfAccountService(db_session)
        
        with pytest.raises(ValidationError) as exc_info:
            service.validate_posting_account(account.id, organization_id)
        
        # Property: Error message should be descriptive
        error_msg = str(exc_info.value)
        
        # Should include the account code for identification
        assert account.account_code in error_msg
        
        # Should describe the reason for failure
        assert len(error_msg) > 20  # Not just a generic error
        
        # Should mention the specific issue
        error_msg_lower = error_msg.lower()
        assert any(keyword in error_msg_lower for keyword in [
            "inactive", "status", "non-posting", "parent", "cannot post"
        ])
