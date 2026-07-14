"""
Tests for BankingAPIProvider abstract base class

Validates that the abstract interface is properly defined and that
concrete implementations must implement all required methods.

Requirements: 13.1
"""

import pytest
from datetime import date
from decimal import Decimal
from app.services.banking_api_provider import (
    BankingAPIProvider,
    AuthenticationResult,
    AccountBalance,
    BankTransaction
)


class TestBankingAPIProviderAbstractClass:
    """Test the abstract base class definition"""
    
    def test_cannot_instantiate_abstract_class(self):
        """Abstract class cannot be instantiated directly"""
        with pytest.raises(TypeError):
            BankingAPIProvider()
    
    def test_concrete_class_must_implement_authenticate(self):
        """Concrete class must implement authenticate method"""
        class IncompleteProvider(BankingAPIProvider):
            def fetch_transactions(self, account_id, date_from, date_to):
                pass
            def fetch_balance(self, account_id):
                pass
        
        with pytest.raises(TypeError):
            IncompleteProvider()
    
    def test_concrete_class_must_implement_fetch_transactions(self):
        """Concrete class must implement fetch_transactions method"""
        class IncompleteProvider(BankingAPIProvider):
            def authenticate(self, credentials):
                pass
            def fetch_balance(self, account_id):
                pass
        
        with pytest.raises(TypeError):
            IncompleteProvider()
    
    def test_concrete_class_must_implement_fetch_balance(self):
        """Concrete class must implement fetch_balance method"""
        class IncompleteProvider(BankingAPIProvider):
            def authenticate(self, credentials):
                pass
            def fetch_transactions(self, account_id, date_from, date_to):
                pass
        
        with pytest.raises(TypeError):
            IncompleteProvider()
    
    def test_complete_concrete_class_can_be_instantiated(self):
        """Concrete class with all methods implemented can be instantiated"""
        class CompleteProvider(BankingAPIProvider):
            def authenticate(self, credentials):
                return AuthenticationResult(success=True)
            
            def fetch_transactions(self, account_id, date_from, date_to):
                return []
            
            def fetch_balance(self, account_id):
                return AccountBalance(
                    current_balance=Decimal("1000.00"),
                    available_balance=Decimal("900.00")
                )
        
        provider = CompleteProvider()
        assert isinstance(provider, BankingAPIProvider)


class TestAuthenticationResult:
    """Test AuthenticationResult data class"""
    
    def test_successful_authentication_result(self):
        """Create successful authentication result"""
        result = AuthenticationResult(success=True, message="Connected")
        assert result.success is True
        assert result.message == "Connected"
        assert result.error_code == ""
    
    def test_failed_authentication_result(self):
        """Create failed authentication result"""
        result = AuthenticationResult(
            success=False,
            message="Invalid credentials",
            error_code="authentication_failed"
        )
        assert result.success is False
        assert result.message == "Invalid credentials"
        assert result.error_code == "authentication_failed"


class TestAccountBalance:
    """Test AccountBalance data class"""
    
    def test_account_balance_creation(self):
        """Create account balance with balances"""
        balance = AccountBalance(
            current_balance=Decimal("5000.00"),
            available_balance=Decimal("4500.00"),
            currency="USD"
        )
        assert balance.current_balance == Decimal("5000.00")
        assert balance.available_balance == Decimal("4500.00")
        assert balance.currency == "USD"
    
    def test_account_balance_without_currency(self):
        """Create account balance without currency"""
        balance = AccountBalance(
            current_balance=Decimal("1000.00"),
            available_balance=Decimal("1000.00")
        )
        assert balance.currency == ""


class TestBankTransaction:
    """Test BankTransaction data class"""
    
    def test_bank_transaction_creation(self):
        """Create bank transaction with all fields"""
        transaction = BankTransaction(
            transaction_id="TXN-123",
            date=date(2024, 1, 15),
            amount=Decimal("250.50"),
            description="Payment received",
            reference="INV-001",
            transaction_type="credit"
        )
        assert transaction.transaction_id == "TXN-123"
        assert transaction.date == date(2024, 1, 15)
        assert transaction.amount == Decimal("250.50")
        assert transaction.description == "Payment received"
        assert transaction.reference == "INV-001"
        assert transaction.transaction_type == "credit"
    
    def test_bank_transaction_defaults(self):
        """Create bank transaction with default values"""
        transaction = BankTransaction(
            transaction_id="TXN-456",
            date=date(2024, 1, 16),
            amount=Decimal("100.00"),
            description="Office supplies"
        )
        assert transaction.reference == ""
        assert transaction.transaction_type == "debit"


class TestConcreteProviderImplementation:
    """Test a complete concrete provider implementation"""
    
    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider for testing"""
        class MockProvider(BankingAPIProvider):
            def authenticate(self, credentials):
                if credentials.get("api_key") == "valid_key":
                    return AuthenticationResult(success=True, message="Authenticated")
                return AuthenticationResult(
                    success=False,
                    message="Invalid API key",
                    error_code="authentication_failed"
                )
            
            def fetch_transactions(self, account_id, date_from, date_to):
                return [
                    BankTransaction(
                        transaction_id="TXN-001",
                        date=date(2024, 1, 15),
                        amount=Decimal("500.00"),
                        description="Deposit",
                        transaction_type="credit"
                    )
                ]
            
            def fetch_balance(self, account_id):
                return AccountBalance(
                    current_balance=Decimal("10000.00"),
                    available_balance=Decimal("9500.00"),
                    currency="USD"
                )
        
        return MockProvider()
    
    def test_authenticate_success(self, mock_provider):
        """Test successful authentication"""
        result = mock_provider.authenticate({"api_key": "valid_key"})
        assert result.success is True
        assert result.message == "Authenticated"
    
    def test_authenticate_failure(self, mock_provider):
        """Test failed authentication"""
        result = mock_provider.authenticate({"api_key": "invalid_key"})
        assert result.success is False
        assert result.error_code == "authentication_failed"
    
    def test_fetch_transactions(self, mock_provider):
        """Test fetching transactions"""
        transactions = mock_provider.fetch_transactions(
            "ACC-123",
            date(2024, 1, 1),
            date(2024, 1, 31)
        )
        assert len(transactions) == 1
        assert transactions[0].transaction_id == "TXN-001"
        assert transactions[0].amount == Decimal("500.00")
    
    def test_fetch_balance(self, mock_provider):
        """Test fetching account balance"""
        balance = mock_provider.fetch_balance("ACC-123")
        assert balance.current_balance == Decimal("10000.00")
        assert balance.available_balance == Decimal("9500.00")
        assert balance.currency == "USD"
