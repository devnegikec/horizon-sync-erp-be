"""Report generation service for Chart of Accounts"""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.base import AccountStatus, AccountType
from app.models.chart_of_account import Account
from app.repositories.chart_of_account_repository import AccountRepository
from app.services.balance_calculator import BalanceCalculator
from app.services.hierarchy_manager import HierarchyManager

logger = logging.getLogger(__name__)


class ReportService:
    """
    Service for generating Chart of Accounts reports.
    
    Supports:
    - Chart of Accounts report (all accounts with balances)
    - Hierarchical report (tree structure with parent-child relationships)
    - Trial Balance report (posting accounts with debit/credit balances)
    - Report filtering by type, status, and date range
    """
    
    def __init__(self, db: Session):
        """
        Initialize report service
        
        Args:
            db: Database session
        """
        self.db = db
        self.repo = AccountRepository(db)
        self.balance_calculator = BalanceCalculator(db)
        self.hierarchy_manager = HierarchyManager(db)
    
    def generate_chart_of_accounts_report(
        self,
        organization_id: UUID,
        account_type: Optional[AccountType] = None,
        status: Optional[AccountStatus] = None,
        as_of_date: Optional[date] = None,
    ) -> dict:
        """
        Generate Chart of Accounts report showing all accounts with their details.
        
        Args:
            organization_id: Organization UUID
            account_type: Filter by account type (optional)
            status: Filter by account status (optional)
            as_of_date: Date to calculate balances as of (defaults to today)
            
        Returns:
            Dictionary containing report data with accounts list
        """
        # Get all accounts with filters
        accounts = self.repo.list_all(
            organization_id=organization_id,
            account_type=account_type,
            status=status,
            sort_by="account_code",
            sort_order="asc"
        )
        
        # Set default date
        if as_of_date is None:
            as_of_date = date.today()
        
        # Build report data
        report_accounts = []
        for account in accounts:
            # Calculate balance
            balance_data = self.balance_calculator.calculate_balance(
                account.id,
                as_of_date=as_of_date,
                use_cache=True
            )
            
            account_data = {
                "id": str(account.id),
                "account_code": account.account_code,
                "account_name": account.account_name,
                "account_type": account.account_type.value if account.account_type else None,
                "status": account.status.value if account.status else None,
                "currency": account.currency,
                "is_posting_account": account.is_posting_account,
                "parent_account_id": str(account.parent_account_id) if account.parent_account_id else None,
                "balance": balance_data["balance"] if balance_data else 0.0,
                "base_currency_balance": balance_data["base_currency_balance"] if balance_data else 0.0,
            }
            report_accounts.append(account_data)
        
        return {
            "report_type": "chart_of_accounts",
            "organization_id": str(organization_id),
            "as_of_date": as_of_date.isoformat(),
            "filters": {
                "account_type": account_type.value if account_type else None,
                "status": status.value if status else None,
            },
            "total_accounts": len(report_accounts),
            "accounts": report_accounts,
        }
    
    def generate_hierarchical_report(
        self,
        organization_id: UUID,
        account_type: Optional[AccountType] = None,
        status: Optional[AccountStatus] = None,
        as_of_date: Optional[date] = None,
    ) -> dict:
        """
        Generate hierarchical report showing accounts in tree structure.
        
        Args:
            organization_id: Organization UUID
            account_type: Filter by account type (optional)
            status: Filter by account status (optional)
            as_of_date: Date to calculate balances as of (defaults to today)
            
        Returns:
            Dictionary containing hierarchical report data
        """
        # Get all accounts with filters
        accounts = self.repo.list_all(
            organization_id=organization_id,
            account_type=account_type,
            status=status,
            sort_by="account_code",
            sort_order="asc"
        )
        
        # Set default date
        if as_of_date is None:
            as_of_date = date.today()
        
        # Build account map for quick lookup
        account_map = {account.id: account for account in accounts}
        
        # Build children map
        children_map = {}
        root_accounts = []
        
        for account in accounts:
            if account.parent_account_id and account.parent_account_id in account_map:
                if account.parent_account_id not in children_map:
                    children_map[account.parent_account_id] = []
                children_map[account.parent_account_id].append(account)
            else:
                root_accounts.append(account)
        
        def build_tree_node(account: Account, level: int = 0) -> dict:
            """Recursively build tree node with children"""
            # Calculate balance
            if account.is_posting_account:
                balance_data = self.balance_calculator.calculate_balance(
                    account.id,
                    as_of_date=as_of_date,
                    use_cache=True
                )
            else:
                # For parent accounts, calculate consolidated balance
                balance_data = self.balance_calculator.calculate_consolidated_balance(
                    account.id,
                    as_of_date=as_of_date,
                    use_cache=True
                )
            
            node = {
                "id": str(account.id),
                "account_code": account.account_code,
                "account_name": account.account_name,
                "account_type": account.account_type.value if account.account_type else None,
                "status": account.status.value if account.status else None,
                "currency": account.currency,
                "is_posting_account": account.is_posting_account,
                "level": level,
                "balance": balance_data["balance"] if balance_data else 0.0,
                "base_currency_balance": balance_data["base_currency_balance"] if balance_data else 0.0,
                "children": []
            }
            
            # Add children recursively
            if account.id in children_map:
                for child in sorted(children_map[account.id], key=lambda a: a.account_code):
                    node["children"].append(build_tree_node(child, level + 1))
            
            return node
        
        # Build tree structure
        tree = [build_tree_node(account) for account in sorted(root_accounts, key=lambda a: a.account_code)]
        
        return {
            "report_type": "hierarchical",
            "organization_id": str(organization_id),
            "as_of_date": as_of_date.isoformat(),
            "filters": {
                "account_type": account_type.value if account_type else None,
                "status": status.value if status else None,
            },
            "total_accounts": len(accounts),
            "tree": tree,
        }
    
    def generate_trial_balance(
        self,
        organization_id: UUID,
        account_type: Optional[AccountType] = None,
        as_of_date: Optional[date] = None,
    ) -> dict:
        """
        Generate trial balance report showing posting accounts with debit/credit balances.
        
        The trial balance must balance: total debits = total credits
        
        Args:
            organization_id: Organization UUID
            account_type: Filter by account type (optional)
            as_of_date: Date to calculate balances as of (defaults to today)
            
        Returns:
            Dictionary containing trial balance report data
        """
        # Get all posting accounts (only leaf nodes can have transactions)
        accounts = self.repo.list_all(
            organization_id=organization_id,
            account_type=account_type,
            status=AccountStatus.ACTIVE,  # Only active accounts in trial balance
            sort_by="account_code",
            sort_order="asc"
        )
        
        # Filter to only posting accounts
        posting_accounts = [a for a in accounts if a.is_posting_account]
        
        # Set default date
        if as_of_date is None:
            as_of_date = date.today()
        
        # Build trial balance data
        trial_balance_accounts = []
        total_debits = Decimal("0")
        total_credits = Decimal("0")
        
        for account in posting_accounts:
            # Calculate balance
            balance_data = self.balance_calculator.calculate_balance(
                account.id,
                as_of_date=as_of_date,
                use_cache=True
            )
            
            if not balance_data:
                continue
            
            debit_balance = Decimal("0")
            credit_balance = Decimal("0")
            
            # Determine debit or credit balance based on account type
            balance = Decimal(str(balance_data["balance"]))
            
            if account.account_type in (AccountType.ASSET, AccountType.EXPENSE):
                # Debit balance accounts
                if balance >= 0:
                    debit_balance = balance
                else:
                    credit_balance = abs(balance)
            else:
                # Credit balance accounts (LIABILITY, EQUITY, REVENUE)
                if balance >= 0:
                    credit_balance = balance
                else:
                    debit_balance = abs(balance)
            
            total_debits += debit_balance
            total_credits += credit_balance
            
            account_data = {
                "id": str(account.id),
                "account_code": account.account_code,
                "account_name": account.account_name,
                "account_type": account.account_type.value if account.account_type else None,
                "currency": account.currency,
                "debit_balance": float(debit_balance),
                "credit_balance": float(credit_balance),
                "debit_total": balance_data["debit_total"],
                "credit_total": balance_data["credit_total"],
            }
            trial_balance_accounts.append(account_data)
        
        # Calculate difference (should be zero for balanced trial balance)
        difference = total_debits - total_credits
        is_balanced = abs(difference) < Decimal("0.01")  # Allow for rounding errors
        
        return {
            "report_type": "trial_balance",
            "organization_id": str(organization_id),
            "as_of_date": as_of_date.isoformat(),
            "filters": {
                "account_type": account_type.value if account_type else None,
            },
            "total_accounts": len(trial_balance_accounts),
            "accounts": trial_balance_accounts,
            "total_debits": float(total_debits),
            "total_credits": float(total_credits),
            "difference": float(difference),
            "is_balanced": is_balanced,
        }
    
    def generate_financial_statement_grouped(
        self,
        organization_id: UUID,
        status: Optional[AccountStatus] = None,
        as_of_date: Optional[date] = None,
    ) -> dict:
        """
        Generate financial statement with accounts grouped by type.
        
        Groups accounts by their account type (Asset, Liability, Equity, Revenue, Expense)
        with proper ordering within each type group.
        
        Args:
            organization_id: Organization UUID
            status: Filter by account status (optional)
            as_of_date: Date to calculate balances as of (defaults to today)
            
        Returns:
            Dictionary containing grouped accounts by type
        """
        # Get all accounts
        accounts = self.repo.list_all(
            organization_id=organization_id,
            status=status,
            sort_by="account_code",
            sort_order="asc"
        )
        
        # Set default date
        if as_of_date is None:
            as_of_date = date.today()
        
        # Group accounts by type
        grouped_accounts = {
            AccountType.ASSET: [],
            AccountType.LIABILITY: [],
            AccountType.EQUITY: [],
            AccountType.REVENUE: [],
            AccountType.EXPENSE: [],
        }
        
        for account in accounts:
            if account.account_type:
                # Calculate balance
                balance_data = self.balance_calculator.calculate_balance(
                    account.id,
                    as_of_date=as_of_date,
                    use_cache=True
                )
                
                account_data = {
                    "id": str(account.id),
                    "account_code": account.account_code,
                    "account_name": account.account_name,
                    "account_type": account.account_type.value,
                    "status": account.status.value if account.status else None,
                    "currency": account.currency,
                    "is_posting_account": account.is_posting_account,
                    "balance": balance_data["balance"] if balance_data else 0.0,
                    "base_currency_balance": balance_data["base_currency_balance"] if balance_data else 0.0,
                }
                
                grouped_accounts[account.account_type].append(account_data)
        
        # Convert to list format with type labels
        result_groups = []
        for account_type in [AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE, AccountType.EXPENSE]:
            if grouped_accounts[account_type]:
                result_groups.append({
                    "account_type": account_type.value,
                    "accounts": grouped_accounts[account_type],
                    "count": len(grouped_accounts[account_type])
                })
        
        return {
            "report_type": "financial_statement_grouped",
            "organization_id": str(organization_id),
            "as_of_date": as_of_date.isoformat(),
            "filters": {
                "status": status.value if status else None,
            },
            "total_accounts": sum(len(group["accounts"]) for group in result_groups),
            "groups": result_groups,
        }

    def generate_financial_statement_grouped(
        self,
        organization_id: UUID,
        status: Optional[AccountStatus] = None,
        as_of_date: Optional[date] = None,
    ) -> dict:
        """
        Generate financial statement with accounts grouped by type.

        Groups accounts by their account type (Asset, Liability, Equity, Revenue, Expense)
        with proper ordering within each type group.

        Args:
            organization_id: Organization UUID
            status: Filter by account status (optional)
            as_of_date: Date to calculate balances as of (defaults to today)

        Returns:
            Dictionary containing grouped accounts by type
        """
        # Get all accounts
        accounts = self.repo.list_all(
            organization_id=organization_id,
            status=status,
            sort_by="account_code",
            sort_order="asc"
        )

        # Set default date
        if as_of_date is None:
            as_of_date = date.today()

        # Group accounts by type
        grouped_accounts = {
            AccountType.ASSET: [],
            AccountType.LIABILITY: [],
            AccountType.EQUITY: [],
            AccountType.REVENUE: [],
            AccountType.EXPENSE: [],
        }

        for account in accounts:
            if account.account_type:
                # Calculate balance
                balance_data = self.balance_calculator.calculate_balance(
                    account.id,
                    as_of_date=as_of_date,
                    use_cache=True
                )

                account_data = {
                    "id": str(account.id),
                    "account_code": account.account_code,
                    "account_name": account.account_name,
                    "account_type": account.account_type.value,
                    "status": account.status.value if account.status else None,
                    "currency": account.currency,
                    "is_posting_account": account.is_posting_account,
                    "balance": balance_data["balance"] if balance_data else 0.0,
                    "base_currency_balance": balance_data["base_currency_balance"] if balance_data else 0.0,
                }

                grouped_accounts[account.account_type].append(account_data)

        # Convert to list format with type labels
        result_groups = []
        for account_type in [AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE, AccountType.EXPENSE]:
            if grouped_accounts[account_type]:
                result_groups.append({
                    "account_type": account_type.value,
                    "accounts": grouped_accounts[account_type],
                    "count": len(grouped_accounts[account_type])
                })

        return {
            "report_type": "financial_statement_grouped",
            "organization_id": str(organization_id),
            "as_of_date": as_of_date.isoformat(),
            "filters": {
                "status": status.value if status else None,
            },
            "total_accounts": sum(len(group["accounts"]) for group in result_groups),
            "groups": result_groups,
        }

