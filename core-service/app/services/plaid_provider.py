"""
Plaid Banking API Provider Stub Implementation

This module provides a stub implementation of the BankingAPIProvider interface
for Plaid integration (US/Canada markets). The methods raise NotImplementedError
to indicate they need to be implemented when actual Plaid integration is added.

Requirements: 13.2, 13.4
"""

from datetime import date
from typing import Dict, List

from app.services.banking_api_provider import (
    BankingAPIProvider,
    AuthenticationResult,
    AccountBalance,
    BankTransaction
)


class PlaidProvider(BankingAPIProvider):
    """
    Stub implementation for Plaid API (US/Canada).
    
    This provider will integrate with Plaid's banking API to fetch
    transactions and account balances for US and Canadian bank accounts.
    
    Expected Credentials:
        - client_id: Plaid client ID (obtained from Plaid dashboard)
        - secret: Plaid secret key (obtained from Plaid dashboard)
        - access_token: Plaid access token for the specific account
                       (obtained through Plaid Link OAuth flow)
    
    API Documentation: https://plaid.com/docs/
    
    Note: This is a stub implementation. All methods raise NotImplementedError
          until actual Plaid integration is implemented.
    """
    
    def authenticate(self, credentials: Dict[str, str]) -> AuthenticationResult:
        """
        Authenticate with the Plaid API.
        
        This method will implement the Plaid OAuth flow to obtain and validate
        access tokens for bank account access.
        
        Args:
            credentials: Dictionary containing:
                - client_id: Plaid client ID
                - secret: Plaid secret key
                - access_token: Plaid access token for the account
        
        Returns:
            AuthenticationResult indicating success or failure
            
        Raises:
            NotImplementedError: Plaid integration is not yet implemented
            
        Example:
            >>> provider = PlaidProvider()
            >>> result = provider.authenticate({
            ...     'client_id': 'your_client_id',
            ...     'secret': 'your_secret',
            ...     'access_token': 'access-sandbox-xxx'
            ... })
        """
        raise NotImplementedError(
            "Plaid authentication is not yet implemented. "
            "This method will use Plaid's OAuth flow to validate credentials "
            "and obtain access tokens for bank account data."
        )
    
    def fetch_transactions(
        self,
        account_id: str,
        date_from: date,
        date_to: date
    ) -> List[BankTransaction]:
        """
        Fetch bank transactions from Plaid API.
        
        This method will call Plaid's /transactions/get endpoint to retrieve
        transaction history for a specific account within the date range.
        
        Args:
            account_id: Plaid account identifier
            date_from: Start date for transaction retrieval (inclusive)
            date_to: End date for transaction retrieval (inclusive)
        
        Returns:
            List of BankTransaction objects in standardized format
            
        Raises:
            NotImplementedError: Plaid integration is not yet implemented
            
        Example:
            >>> provider = PlaidProvider()
            >>> transactions = provider.fetch_transactions(
            ...     account_id='plaid_account_id',
            ...     date_from=date(2024, 1, 1),
            ...     date_to=date(2024, 1, 31)
            ... )
        """
        raise NotImplementedError(
            "Plaid transaction fetching is not yet implemented. "
            "This method will call Plaid's /transactions/get endpoint "
            "to retrieve transaction history for the specified date range."
        )
    
    def fetch_balance(self, account_id: str) -> AccountBalance:
        """
        Fetch account balance from Plaid API.
        
        This method will call Plaid's /accounts/balance/get endpoint to retrieve
        current and available balance information for a specific account.
        
        Args:
            account_id: Plaid account identifier
        
        Returns:
            AccountBalance containing current_balance and available_balance
            
        Raises:
            NotImplementedError: Plaid integration is not yet implemented
            
        Example:
            >>> provider = PlaidProvider()
            >>> balance = provider.fetch_balance(account_id='plaid_account_id')
            >>> print(f"Current: {balance.current_balance}, Available: {balance.available_balance}")
        """
        raise NotImplementedError(
            "Plaid balance fetching is not yet implemented. "
            "This method will call Plaid's /accounts/balance/get endpoint "
            "to retrieve current and available balance information."
        )
