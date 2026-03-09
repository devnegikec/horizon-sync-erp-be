"""
Tests for SaltEdgeProvider stub implementation

Validates that SaltEdgeProvider properly implements the BankingAPIProvider
interface and raises NotImplementedError for all methods until actual
Salt Edge integration is implemented.

Requirements: 13.3, 13.5
"""

import pytest
from datetime import date
from app.services.salt_edge_provider import SaltEdgeProvider
from app.services.banking_api_provider import BankingAPIProvider


class TestSaltEdgeProviderStub:
    """Test SaltEdgeProvider stub implementation"""
    
    @pytest.fixture
    def salt_edge_provider(self):
        """Create SaltEdgeProvider instance"""
        return SaltEdgeProvider()
    
    def test_salt_edge_provider_is_banking_api_provider(self, salt_edge_provider):
        """SaltEdgeProvider implements BankingAPIProvider interface"""
        assert isinstance(salt_edge_provider, BankingAPIProvider)
    
    def test_salt_edge_provider_can_be_instantiated(self):
        """SaltEdgeProvider can be instantiated (all abstract methods implemented)"""
        provider = SaltEdgeProvider()
        assert provider is not None
    
    def test_authenticate_raises_not_implemented(self, salt_edge_provider):
        """authenticate method raises NotImplementedError"""
        credentials = {
            'app_id': 'test_app_id',
            'secret': 'test_secret',
            'customer_id': 'customer_xxx'
        }
        
        with pytest.raises(NotImplementedError) as exc_info:
            salt_edge_provider.authenticate(credentials)
        
        assert "Salt Edge authentication is not yet implemented" in str(exc_info.value)
    
    def test_fetch_transactions_raises_not_implemented(self, salt_edge_provider):
        """fetch_transactions method raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            salt_edge_provider.fetch_transactions(
                account_id='salt_edge_account_id',
                date_from=date(2024, 1, 1),
                date_to=date(2024, 1, 31)
            )
        
        assert "Salt Edge transaction fetching is not yet implemented" in str(exc_info.value)
    
    def test_fetch_balance_raises_not_implemented(self, salt_edge_provider):
        """fetch_balance method raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            salt_edge_provider.fetch_balance(account_id='salt_edge_account_id')
        
        assert "Salt Edge balance fetching is not yet implemented" in str(exc_info.value)
    
    def test_authenticate_error_message_mentions_authentication_flow(self, salt_edge_provider):
        """authenticate error message mentions authentication flow"""
        with pytest.raises(NotImplementedError) as exc_info:
            salt_edge_provider.authenticate({})
        
        assert "authentication" in str(exc_info.value).lower()
    
    def test_fetch_transactions_error_message_mentions_endpoint(self, salt_edge_provider):
        """fetch_transactions error message mentions Salt Edge endpoint"""
        with pytest.raises(NotImplementedError) as exc_info:
            salt_edge_provider.fetch_transactions('acc', date(2024, 1, 1), date(2024, 1, 31))
        
        assert "transactions endpoint" in str(exc_info.value)
    
    def test_fetch_balance_error_message_mentions_endpoint(self, salt_edge_provider):
        """fetch_balance error message mentions Salt Edge endpoint"""
        with pytest.raises(NotImplementedError) as exc_info:
            salt_edge_provider.fetch_balance('acc')
        
        assert "accounts endpoint" in str(exc_info.value)


class TestSaltEdgeProviderDocumentation:
    """Test SaltEdgeProvider documentation and expected credentials"""
    
    def test_class_docstring_documents_credentials(self):
        """Class docstring documents expected credentials"""
        docstring = SaltEdgeProvider.__doc__
        assert "app_id" in docstring
        assert "secret" in docstring
        assert "customer_id" in docstring
    
    def test_class_docstring_mentions_european_markets(self):
        """Class docstring mentions European/global markets"""
        docstring = SaltEdgeProvider.__doc__
        assert "EU" in docstring or "Europe" in docstring or "global" in docstring
    
    def test_authenticate_docstring_documents_credentials(self):
        """authenticate method docstring documents credentials"""
        docstring = SaltEdgeProvider.authenticate.__doc__
        assert "app_id" in docstring
        assert "secret" in docstring
        assert "customer_id" in docstring
    
    def test_fetch_transactions_docstring_has_example(self):
        """fetch_transactions method docstring includes usage example"""
        docstring = SaltEdgeProvider.fetch_transactions.__doc__
        assert "Example:" in docstring or ">>>" in docstring
    
    def test_fetch_balance_docstring_has_example(self):
        """fetch_balance method docstring includes usage example"""
        docstring = SaltEdgeProvider.fetch_balance.__doc__
        assert "Example:" in docstring or ">>>" in docstring
