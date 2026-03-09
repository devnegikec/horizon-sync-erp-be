"""
Tests for PlaidProvider stub implementation

Validates that PlaidProvider properly implements the BankingAPIProvider
interface and raises NotImplementedError for all methods until actual
Plaid integration is implemented.

Requirements: 13.2, 13.4
"""

import pytest
from datetime import date
from app.services.plaid_provider import PlaidProvider
from app.services.banking_api_provider import BankingAPIProvider


class TestPlaidProviderStub:
    """Test PlaidProvider stub implementation"""
    
    @pytest.fixture
    def plaid_provider(self):
        """Create PlaidProvider instance"""
        return PlaidProvider()
    
    def test_plaid_provider_is_banking_api_provider(self, plaid_provider):
        """PlaidProvider implements BankingAPIProvider interface"""
        assert isinstance(plaid_provider, BankingAPIProvider)
    
    def test_plaid_provider_can_be_instantiated(self):
        """PlaidProvider can be instantiated (all abstract methods implemented)"""
        provider = PlaidProvider()
        assert provider is not None
    
    def test_authenticate_raises_not_implemented(self, plaid_provider):
        """authenticate method raises NotImplementedError"""
        credentials = {
            'client_id': 'test_client_id',
            'secret': 'test_secret',
            'access_token': 'access-sandbox-xxx'
        }
        
        with pytest.raises(NotImplementedError) as exc_info:
            plaid_provider.authenticate(credentials)
        
        assert "Plaid authentication is not yet implemented" in str(exc_info.value)
    
    def test_fetch_transactions_raises_not_implemented(self, plaid_provider):
        """fetch_transactions method raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            plaid_provider.fetch_transactions(
                account_id='plaid_account_id',
                date_from=date(2024, 1, 1),
                date_to=date(2024, 1, 31)
            )
        
        assert "Plaid transaction fetching is not yet implemented" in str(exc_info.value)
    
    def test_fetch_balance_raises_not_implemented(self, plaid_provider):
        """fetch_balance method raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            plaid_provider.fetch_balance(account_id='plaid_account_id')
        
        assert "Plaid balance fetching is not yet implemented" in str(exc_info.value)
    
    def test_authenticate_error_message_mentions_oauth(self, plaid_provider):
        """authenticate error message mentions OAuth flow"""
        with pytest.raises(NotImplementedError) as exc_info:
            plaid_provider.authenticate({})
        
        assert "OAuth" in str(exc_info.value)
    
    def test_fetch_transactions_error_message_mentions_endpoint(self, plaid_provider):
        """fetch_transactions error message mentions Plaid endpoint"""
        with pytest.raises(NotImplementedError) as exc_info:
            plaid_provider.fetch_transactions('acc', date(2024, 1, 1), date(2024, 1, 31))
        
        assert "/transactions/get" in str(exc_info.value)
    
    def test_fetch_balance_error_message_mentions_endpoint(self, plaid_provider):
        """fetch_balance error message mentions Plaid endpoint"""
        with pytest.raises(NotImplementedError) as exc_info:
            plaid_provider.fetch_balance('acc')
        
        assert "/accounts/balance/get" in str(exc_info.value)


class TestPlaidProviderDocumentation:
    """Test PlaidProvider documentation and expected credentials"""
    
    def test_class_docstring_documents_credentials(self):
        """Class docstring documents expected credentials"""
        docstring = PlaidProvider.__doc__
        assert "client_id" in docstring
        assert "secret" in docstring
        assert "access_token" in docstring
    
    def test_class_docstring_mentions_us_canada(self):
        """Class docstring mentions US/Canada markets"""
        docstring = PlaidProvider.__doc__
        assert "US" in docstring or "Canada" in docstring
    
    def test_authenticate_docstring_documents_credentials(self):
        """authenticate method docstring documents credentials"""
        docstring = PlaidProvider.authenticate.__doc__
        assert "client_id" in docstring
        assert "secret" in docstring
        assert "access_token" in docstring
    
    def test_fetch_transactions_docstring_has_example(self):
        """fetch_transactions method docstring includes usage example"""
        docstring = PlaidProvider.fetch_transactions.__doc__
        assert "Example:" in docstring or ">>>" in docstring
    
    def test_fetch_balance_docstring_has_example(self):
        """fetch_balance method docstring includes usage example"""
        docstring = PlaidProvider.fetch_balance.__doc__
        assert "Example:" in docstring or ">>>" in docstring
