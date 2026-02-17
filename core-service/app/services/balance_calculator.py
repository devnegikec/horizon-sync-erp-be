"""Balance calculator service for account balances"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.cache import cache, get_balance_cache_key, invalidate_account_balance_cache
from app.models.account_balance import AccountBalance
from app.models.base import AccountType
from app.models.chart_of_account import Account
from app.models.journal_entry import JournalEntryLine, JournalEntry
from app.models.base import JournalStatus
from app.services.currency_service import CurrencyService
from app.services.hierarchy_manager import HierarchyManager

logger = logging.getLogger(__name__)


class BalanceCalculator:
    """
    Service for calculating and caching account balances.
    
    Handles:
    - Real-time balance calculation from journal entries
    - Natural balance direction based on account type
    - Consolidated balances for parent accounts
    - Historical balance queries
    - Balance caching with Redis
    """
    
    def __init__(
        self,
        db: Session,
        currency_service: Optional[CurrencyService] = None,
        hierarchy_manager: Optional[HierarchyManager] = None
    ):
        """
        Initialize balance calculator
        
        Args:
            db: Database session
            currency_service: Currency service for conversions
            hierarchy_manager: Hierarchy manager for parent account calculations
        """
        self.db = db
        self.currency_service = currency_service or CurrencyService(db)
        self.hierarchy_manager = hierarchy_manager or HierarchyManager(db)
    
    def _get_natural_balance(
        self,
        account_type: AccountType,
        debit_total: Decimal,
        credit_total: Decimal
    ) -> Decimal:
        """
        Calculate balance based on account type's natural balance direction
        
        Assets and Expenses: Debit increases, Credit decreases (Balance = Debit - Credit)
        Liabilities, Equity, Revenue: Credit increases, Debit decreases (Balance = Credit - Debit)
        
        Args:
            account_type: Type of account
            debit_total: Total debits
            credit_total: Total credits
            
        Returns:
            Net balance
        """
        if account_type in (AccountType.ASSET, AccountType.EXPENSE):
            # Debit balance accounts
            return debit_total - credit_total
        else:
            # Credit balance accounts (LIABILITY, EQUITY, REVENUE)
            return credit_total - debit_total
    
    def calculate_balance(
        self,
        account_id: UUID,
        as_of_date: Optional[date] = None,
        use_cache: bool = True
    ) -> Optional[dict]:
        """
        Calculate account balance as of a specific date
        
        Args:
            account_id: Account UUID
            as_of_date: Date to calculate balance as of (defaults to today)
            use_cache: Whether to use cached balance if available
            
        Returns:
            Dictionary with balance information or None if account not found
        """
        # Check cache first if enabled
        if use_cache:
            cache_key = get_balance_cache_key(account_id, as_of_date.isoformat() if as_of_date else None)
            cached = cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for balance: {cache_key}")
                return cached
        
        # Get account
        account = self.db.query(Account).filter(Account.id == account_id).first()
        if not account:
            logger.warning(f"Account not found: {account_id}")
            return None
        
        # Set default date to today if not provided
        if as_of_date is None:
            as_of_date = date.today()
        
        # Query journal entry lines for this account up to the specified date
        query = (
            self.db.query(
                func.sum(JournalEntryLine.debit).label("debit_total"),
                func.sum(JournalEntryLine.credit).label("credit_total")
            )
            .join(JournalEntry, JournalEntryLine.journal_entry_id == JournalEntry.id)
            .filter(
                and_(
                    JournalEntryLine.account_id == account_id,
                    JournalEntry.status == JournalStatus.POSTED,
                    func.date(JournalEntry.posting_date) <= as_of_date
                )
            )
        )
        
        try:
            result = query.first()
            debit_total = result.debit_total or Decimal("0")
            credit_total = result.credit_total or Decimal("0")
        except (ProgrammingError, OperationalError) as error:
            logger.warning(
                "Balance query fallback to zero totals due to missing journal schema for account %s: %s",
                account_id,
                error,
            )
            self.db.rollback()
            debit_total = Decimal("0")
            credit_total = Decimal("0")
        
        # Calculate balance based on natural balance direction
        balance = self._get_natural_balance(account.account_type, debit_total, credit_total)
        
        # Convert to base currency if needed
        base_currency = self.currency_service.get_base_currency()
        base_currency_balance = balance
        
        if account.currency != base_currency:
            try:
                base_currency_balance = self.currency_service.convert(
                    amount=float(balance),
                    from_currency=account.currency,
                    to_currency=base_currency,
                    date=as_of_date
                )
                base_currency_balance = Decimal(str(base_currency_balance))
            except Exception as e:
                logger.warning(f"Currency conversion failed for account {account_id}: {e}")
                base_currency_balance = balance
        
        # Prepare result
        balance_data = {
            "account_id": str(account_id),
            "currency": account.currency,
            "debit_total": float(debit_total),
            "credit_total": float(credit_total),
            "balance": float(balance),
            "base_currency_balance": float(base_currency_balance),
            "as_of_date": as_of_date.isoformat(),
            "account_type": account.account_type.value,
            "account_code": account.account_code,
            "account_name": account.account_name
        }
        
        # Cache the result
        if use_cache:
            cache_key = get_balance_cache_key(account_id, as_of_date.isoformat() if as_of_date else None)
            cache.set(cache_key, balance_data, ttl=3600)  # Cache for 1 hour
        
        return balance_data
    
    def calculate_consolidated_balance(
        self,
        parent_account_id: UUID,
        as_of_date: Optional[date] = None,
        use_cache: bool = True
    ) -> Optional[dict]:
        """
        Calculate consolidated balance for a parent account by summing all child balances
        
        Args:
            parent_account_id: Parent account UUID
            as_of_date: Date to calculate balance as of (defaults to today)
            use_cache: Whether to use cached balances
            
        Returns:
            Dictionary with consolidated balance information
        """
        # Get parent account
        parent_account = self.db.query(Account).filter(Account.id == parent_account_id).first()
        if not parent_account:
            logger.warning(f"Parent account not found: {parent_account_id}")
            return None
        
        # Get all descendant accounts
        descendants = self.hierarchy_manager.get_descendants(parent_account_id)
        
        # If no descendants, calculate balance for the parent itself
        if not descendants:
            return self.calculate_balance(parent_account_id, as_of_date, use_cache)
        
        # Calculate balance for each descendant
        total_balance = Decimal("0")
        total_base_currency_balance = Decimal("0")
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        
        for descendant in descendants:
            # Only include posting accounts (leaf nodes)
            if descendant.is_posting_account:
                balance_data = self.calculate_balance(descendant.id, as_of_date, use_cache)
                if balance_data:
                    total_debit += Decimal(str(balance_data["debit_total"]))
                    total_credit += Decimal(str(balance_data["credit_total"]))
                    total_base_currency_balance += Decimal(str(balance_data["base_currency_balance"]))
        
        # Calculate consolidated balance based on parent account type
        total_balance = self._get_natural_balance(
            parent_account.account_type,
            total_debit,
            total_credit
        )
        
        # Prepare result
        consolidated_data = {
            "account_id": str(parent_account_id),
            "currency": parent_account.currency,
            "debit_total": float(total_debit),
            "credit_total": float(total_credit),
            "balance": float(total_balance),
            "base_currency_balance": float(total_base_currency_balance),
            "as_of_date": (as_of_date or date.today()).isoformat(),
            "account_type": parent_account.account_type.value,
            "account_code": parent_account.account_code,
            "account_name": parent_account.account_name,
            "is_consolidated": True,
            "child_count": len(descendants)
        }
        
        return consolidated_data
    
    def invalidate_cache(self, account_id: UUID) -> int:
        """
        Invalidate all cached balances for an account
        
        Args:
            account_id: Account UUID
            
        Returns:
            Number of cache entries deleted
        """
        count = invalidate_account_balance_cache(account_id)
        logger.info(f"Invalidated {count} cache entries for account {account_id}")
        return count
    
    def invalidate_hierarchy_cache(self, account_id: UUID) -> int:
        """
        Invalidate cache for an account and all its ancestors
        (used when a transaction affects child accounts)
        
        Args:
            account_id: Account UUID
            
        Returns:
            Total number of cache entries deleted
        """
        total_deleted = 0
        
        # Invalidate the account itself
        total_deleted += self.invalidate_cache(account_id)
        
        # Invalidate all ancestors
        ancestors = self.hierarchy_manager.get_ancestors(account_id)
        for ancestor in ancestors:
            total_deleted += self.invalidate_cache(ancestor.id)
        
        logger.info(f"Invalidated {total_deleted} cache entries in hierarchy for account {account_id}")
        return total_deleted
    
    def refresh_cache(self, account_id: UUID, as_of_date: Optional[date] = None) -> bool:
        """
        Refresh cached balance for an account
        
        Args:
            account_id: Account UUID
            as_of_date: Date to calculate balance as of
            
        Returns:
            True if successful
        """
        try:
            # Invalidate existing cache
            self.invalidate_cache(account_id)
            
            # Recalculate and cache
            self.calculate_balance(account_id, as_of_date, use_cache=True)
            
            logger.info(f"Refreshed cache for account {account_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh cache for account {account_id}: {e}")
            return False
    
    def get_balance_history(
        self,
        account_id: UUID,
        start_date: date,
        end_date: date
    ) -> list[dict]:
        """
        Get balance history for an account over a date range
        
        Args:
            account_id: Account UUID
            start_date: Start date
            end_date: End date
            
        Returns:
            List of balance snapshots
        """
        history = []
        current_date = start_date
        
        while current_date <= end_date:
            balance_data = self.calculate_balance(account_id, current_date, use_cache=True)
            if balance_data:
                history.append(balance_data)
            
            # Move to next day
            from datetime import timedelta
            current_date += timedelta(days=1)
        
        return history
