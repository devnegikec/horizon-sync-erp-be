"""
Salt Edge Banking API Provider Stub Implementation

This module provides a stub implementation of the BankingAPIProvider interface
for Salt Edge integration (European and global markets). The methods raise 
NotImplementedError to indicate they need to be implemented when actual 
Salt Edge integration is added.

Requirements: 13.3, 13.5
"""

from datetime import date
from typing import Dict, List

from app.services.banking_api_provider import (
    BankingAPIProvider,
    AuthenticationResult,
    AccountBalance,
    BankTransaction
)


class SaltEdgeProvider(BankingAPIProvider):
    """
    Stub implementation for Salt Edge API (EU/Global).
    
    This provider will integrate with Salt Edge's banking API to fetch
    transactions and account balances for European and global bank accounts.
    Salt Edge supports over 5,000 banks across Europe, Asia, and other regions.
    
    Expected Credentials:
        - app_id: Salt Edge application ID (obtained from Salt Edge dashboard)
        - secret: Salt Edge secret key (obtained from Salt Edge dashboard)
        - customer_id: Salt Edge customer identifier (unique per end-user)
    
    API Documentation: https://docs.saltedge.com/
    
    Note: This is a stub implementation. All methods raise NotImplementedError
          until actual Salt Edge integration is implemented.
    """
    
    def authenticate(self, credentials: Dict[str, str]) -> AuthenticationResult:
        """
        Authenticate with the Salt Edge API.
        
        This method will implement the Salt Edge authentication flow to validate
        credentials and establish a connection for accessing bank account data.
        
        Args:
            credentials: Dictionary containing:
                - app_id: Salt Edge application ID
                - secret: Salt Edge secret key
                - customer_id: Salt Edge customer identifier
        
        Returns:
            AuthenticationResult indicating success or failure
            
        Raises:
            NotImplementedError: Salt Edge integration is not yet implemented
            
        Example:
            >>> provider = SaltEdgeProvider()
            >>> result = provider.authenticate({
            ...     'app_id': 'your_app_id',
            ...     'secret': 'your_secret',
            ...     'customer_id': 'customer_xxx'
            ... })
        """
        raise NotImplementedError(
            "Salt Edge authentication is not yet implemented. "
            "This method will use Salt Edge's authentication flow to validate "
            "credentials and establish access to bank account data."
        )
    
    def fetch_transactions(
        self,
        account_id: str,
        date_from: date,
        date_to: date
    ) -> List[BankTransaction]:
        """
        Fetch bank transactions from Salt Edge API.
        
        This method will call Salt Edge's transactions endpoint to retrieve
        transaction history for a specific account within the date range.
        
        Args:
            account_id: Salt Edge account identifier
            date_from: Start date for transaction retrieval (inclusive)
            date_to: End date for transaction retrieval (inclusive)
        
        Returns:
            List of BankTransaction objects in standardized format
            
        Raises:
            NotImplementedError: Salt Edge integration is not yet implemented
            
        Example:
            >>> provider = SaltEdgeProvider()
            >>> transactions = provider.fetch_transactions(
            ...     account_id='salt_edge_account_id',
            ...     date_from=date(2024, 1, 1),
            ...     date_to=date(2024, 1, 31)
            ... )
        """
        raise NotImplementedError(
            "Salt Edge transaction fetching is not yet implemented. "
            "This method will call Salt Edge's transactions endpoint "
            "to retrieve transaction history for the specified date range."
        )
    
    def fetch_balance(self, account_id: str) -> AccountBalance:
        """
        Fetch account balance from Salt Edge API.
        
        This method will call Salt Edge's accounts endpoint to retrieve
        current and available balance information for a specific account.
        
        Args:
            account_id: Salt Edge account identifier
        
        Returns:
            AccountBalance containing current_balance and available_balance
            
        Raises:
            NotImplementedError: Salt Edge integration is not yet implemented
            
        Example:
            >>> provider = SaltEdgeProvider()
            >>> balance = provider.fetch_balance(account_id='salt_edge_account_id')
            >>> print(f"Current: {balance.current_balance}, Available: {balance.available_balance}")
        """
        raise NotImplementedError(
            "Salt Edge balance fetching is not yet implemented. "
            "This method will call Salt Edge's accounts endpoint "
            "to retrieve current and available balance information."
        )
