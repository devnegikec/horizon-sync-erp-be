"""
Banking API Provider Abstract Base Class

This module defines the abstract interface for banking API providers.
Concrete implementations (Plaid, Salt Edge) will implement these methods
to provide banking data integration.

Requirements: 13.1
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Dict, List, Any
from decimal import Decimal


class AuthenticationResult:
    """Result of authentication attempt with a banking API provider"""
    
    def __init__(self, success: bool, message: str = "", error_code: str = ""):
        self.success = success
        self.message = message
        self.error_code = error_code


class AccountBalance:
    """Account balance information from banking API"""
    
    def __init__(self, current_balance: Decimal, available_balance: Decimal, currency: str = ""):
        self.current_balance = current_balance
        self.available_balance = available_balance
        self.currency = currency


class BankTransaction:
    """Standardized bank transaction format from API providers"""
    
    def __init__(
        self,
        transaction_id: str,
        date: date,
        amount: Decimal,
        description: str,
        reference: str = "",
        transaction_type: str = "debit"
    ):
        self.transaction_id = transaction_id
        self.date = date
        self.amount = amount
        self.description = description
        self.reference = reference
        self.transaction_type = transaction_type


class BankingAPIProvider(ABC):
    """
    Abstract base class for banking API providers.
    
    This interface defines the contract that all banking API providers
    (Plaid, Salt Edge, etc.) must implement to integrate with the system.
    
    The provider handles:
    - Authentication with the banking API
    - Fetching transactions from bank accounts
    - Fetching account balance information
    """
    
    @abstractmethod
    def authenticate(self, credentials: Dict[str, str]) -> AuthenticationResult:
        """
        Authenticate with the banking API provider.
        
        Args:
            credentials: Dictionary containing provider-specific credentials
                        (e.g., client_id, secret, access_token for Plaid)
        
        Returns:
            AuthenticationResult indicating success or failure
            
        Raises:
            NotImplementedError: Must be implemented by concrete provider
        """
        pass
    
    @abstractmethod
    def fetch_transactions(
        self,
        account_id: str,
        date_from: date,
        date_to: date
    ) -> List[BankTransaction]:
        """
        Fetch bank transactions for a specific account within a date range.
        
        Args:
            account_id: Provider-specific account identifier
            date_from: Start date for transaction retrieval
            date_to: End date for transaction retrieval
        
        Returns:
            List of BankTransaction objects in standardized format
            
        Raises:
            NotImplementedError: Must be implemented by concrete provider
        """
        pass
    
    @abstractmethod
    def fetch_balance(self, account_id: str) -> AccountBalance:
        """
        Fetch current account balance information.
        
        Args:
            account_id: Provider-specific account identifier
        
        Returns:
            AccountBalance containing current and available balance
            
        Raises:
            NotImplementedError: Must be implemented by concrete provider
        """
        pass
