"""Default account structure template for chart of accounts setup"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.models.base import AccountType


@dataclass
class AccountTemplate:
    """Template for creating default GL accounts"""

    account_code: str
    account_name: str
    account_type: AccountType
    parent_code: str | None = None
    is_group: bool = False
    is_posting_account: bool = True
    description: str | None = None
    level: int = 1


@lru_cache(maxsize=1)
def get_default_account_structure() -> list[AccountTemplate]:
    """
    Get the standard default account structure.

    This function returns a list of account templates that form a complete
    chart of accounts following standard accounting practices. The structure
    includes all five account types (ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE)
    with hierarchical parent-child relationships.

    The account codes follow standard numbering:
    - 1000-1999: ASSET accounts
    - 2000-2999: LIABILITY accounts
    - 3000-3999: EQUITY accounts
    - 4000-4999: REVENUE accounts
    - 5000-5999: EXPENSE accounts

    Returns:
        list[AccountTemplate]: List of account templates for default chart creation
    """
    return [
        # ===== ASSETS (1000-1999) =====
        # Current Assets (1000-1499)
        AccountTemplate(
            account_code="1000",
            account_name="Cash and Bank Accounts",
            account_type=AccountType.ASSET,
            is_group=True,
            is_posting_account=False,
            description="Cash on hand and bank account balances",
            level=1,
        ),
        AccountTemplate(
            account_code="1010",
            account_name="Cash",
            account_type=AccountType.ASSET,
            parent_code="1000",
            description="Cash on hand",
            level=2,
        ),
        AccountTemplate(
            account_code="1020",
            account_name="Bank Accounts",
            account_type=AccountType.ASSET,
            parent_code="1000",
            description="Bank account balances",
            level=2,
        ),
        AccountTemplate(
            account_code="1200",
            account_name="Accounts Receivable",
            account_type=AccountType.ASSET,
            description="Amounts owed by customers",
            level=1,
        ),
        AccountTemplate(
            account_code="1300",
            account_name="Inventory",
            account_type=AccountType.ASSET,
            description="Value of goods held for sale",
            level=1,
        ),
        AccountTemplate(
            account_code="1400",
            account_name="Prepaid Expenses",
            account_type=AccountType.ASSET,
            description="Expenses paid in advance",
            level=1,
        ),
        # Fixed Assets (1500-1999)
        AccountTemplate(
            account_code="1500",
            account_name="Property and Equipment",
            account_type=AccountType.ASSET,
            is_group=True,
            is_posting_account=False,
            description="Long-term tangible assets",
            level=1,
        ),
        AccountTemplate(
            account_code="1510",
            account_name="Land and Buildings",
            account_type=AccountType.ASSET,
            parent_code="1500",
            description="Real estate owned",
            level=2,
        ),
        AccountTemplate(
            account_code="1520",
            account_name="Equipment",
            account_type=AccountType.ASSET,
            parent_code="1500",
            description="Machinery and equipment",
            level=2,
        ),
        AccountTemplate(
            account_code="1530",
            account_name="Vehicles",
            account_type=AccountType.ASSET,
            parent_code="1500",
            description="Company vehicles",
            level=2,
        ),
        AccountTemplate(
            account_code="1600",
            account_name="Accumulated Depreciation",
            account_type=AccountType.ASSET,
            description="Contra-asset account for depreciation",
            level=1,
        ),
        # ===== LIABILITIES (2000-2999) =====
        # Current Liabilities (2000-2499)
        AccountTemplate(
            account_code="2000",
            account_name="Accounts Payable",
            account_type=AccountType.LIABILITY,
            description="Amounts owed to suppliers",
            level=1,
        ),
        AccountTemplate(
            account_code="2100",
            account_name="Accrued Expenses",
            account_type=AccountType.LIABILITY,
            description="Expenses incurred but not yet paid",
            level=1,
        ),
        AccountTemplate(
            account_code="2200",
            account_name="Short-term Debt",
            account_type=AccountType.LIABILITY,
            description="Loans and debt due within one year",
            level=1,
        ),
        AccountTemplate(
            account_code="2300",
            account_name="Sales Tax Payable",
            account_type=AccountType.LIABILITY,
            description="Sales tax collected from customers",
            level=1,
        ),
        AccountTemplate(
            account_code="2400",
            account_name="Payroll Liabilities",
            account_type=AccountType.LIABILITY,
            description="Wages and payroll taxes payable",
            level=1,
        ),
        # Long-term Liabilities (2500-2999)
        AccountTemplate(
            account_code="2500",
            account_name="Long-term Debt",
            account_type=AccountType.LIABILITY,
            description="Loans and debt due after one year",
            level=1,
        ),
        # ===== EQUITY (3000-3999) =====
        AccountTemplate(
            account_code="3000",
            account_name="Owner's Equity",
            account_type=AccountType.EQUITY,
            description="Owner's investment in the business",
            level=1,
        ),
        AccountTemplate(
            account_code="3100",
            account_name="Retained Earnings",
            account_type=AccountType.EQUITY,
            description="Accumulated profits retained in the business",
            level=1,
        ),
        AccountTemplate(
            account_code="3200",
            account_name="Current Year Earnings",
            account_type=AccountType.EQUITY,
            description="Net income for the current fiscal year",
            level=1,
        ),
        # ===== REVENUE (4000-4999) =====
        AccountTemplate(
            account_code="4000",
            account_name="Sales Revenue",
            account_type=AccountType.REVENUE,
            description="Revenue from sale of goods",
            level=1,
        ),
        AccountTemplate(
            account_code="4100",
            account_name="Service Revenue",
            account_type=AccountType.REVENUE,
            description="Revenue from services provided",
            level=1,
        ),
        AccountTemplate(
            account_code="4200",
            account_name="Interest Income",
            account_type=AccountType.REVENUE,
            description="Interest earned on investments and deposits",
            level=1,
        ),
        AccountTemplate(
            account_code="4900",
            account_name="Other Income",
            account_type=AccountType.REVENUE,
            description="Miscellaneous income",
            level=1,
        ),
        # ===== EXPENSES (5000-5999) =====
        AccountTemplate(
            account_code="5000",
            account_name="Cost of Goods Sold",
            account_type=AccountType.EXPENSE,
            description="Direct costs of producing goods sold",
            level=1,
        ),
        AccountTemplate(
            account_code="5100",
            account_name="Operating Expenses",
            account_type=AccountType.EXPENSE,
            is_group=True,
            is_posting_account=False,
            description="General business operating expenses",
            level=1,
        ),
        AccountTemplate(
            account_code="5110",
            account_name="Office Supplies",
            account_type=AccountType.EXPENSE,
            parent_code="5100",
            description="Office supplies and materials",
            level=2,
        ),
        AccountTemplate(
            account_code="5120",
            account_name="Marketing and Advertising",
            account_type=AccountType.EXPENSE,
            parent_code="5100",
            description="Marketing and advertising costs",
            level=2,
        ),
        AccountTemplate(
            account_code="5200",
            account_name="Salaries and Wages",
            account_type=AccountType.EXPENSE,
            description="Employee compensation",
            level=1,
        ),
        AccountTemplate(
            account_code="5300",
            account_name="Rent Expense",
            account_type=AccountType.EXPENSE,
            description="Rent for office and facilities",
            level=1,
        ),
        AccountTemplate(
            account_code="5400",
            account_name="Utilities Expense",
            account_type=AccountType.EXPENSE,
            description="Electricity, water, gas, and other utilities",
            level=1,
        ),
        AccountTemplate(
            account_code="5500",
            account_name="Insurance Expense",
            account_type=AccountType.EXPENSE,
            description="Business insurance premiums",
            level=1,
        ),
        AccountTemplate(
            account_code="5600",
            account_name="Depreciation Expense",
            account_type=AccountType.EXPENSE,
            description="Depreciation of fixed assets",
            level=1,
        ),
        AccountTemplate(
            account_code="5700",
            account_name="Interest Expense",
            account_type=AccountType.EXPENSE,
            description="Interest paid on loans and debt",
            level=1,
        ),
        AccountTemplate(
            account_code="5800",
            account_name="Travel and Entertainment",
            account_type=AccountType.EXPENSE,
            description="Business travel and entertainment expenses",
            level=1,
        ),
        AccountTemplate(
            account_code="5900",
            account_name="Professional Fees",
            account_type=AccountType.EXPENSE,
            description="Legal, accounting, and consulting fees",
            level=1,
        ),
    ]


# Default account mappings for transaction types
# Maps transaction types to appropriate account codes from the default structure
DEFAULT_MAPPINGS: dict[str, dict[str, Any]] = {
    # Payment-related mappings
    "payment_cash": {
        "transaction_type": "payment",
        "scenario": "cash",
        "account_code": "1010",  # Cash
    },
    "payment_bank": {
        "transaction_type": "payment",
        "scenario": "bank",
        "account_code": "1020",  # Bank Accounts
    },
    # Receivables
    "accounts_receivable": {
        "transaction_type": "sales_invoice",
        "scenario": "receivable",
        "account_code": "1200",  # Accounts Receivable
    },
    # Payables
    "accounts_payable": {
        "transaction_type": "purchase_invoice",
        "scenario": "payable",
        "account_code": "2000",  # Accounts Payable
    },
    # Revenue
    "sales_revenue": {
        "transaction_type": "sales_invoice",
        "scenario": "revenue",
        "account_code": "4000",  # Sales Revenue
    },
    # Expenses
    "purchase_expense": {
        "transaction_type": "purchase_invoice",
        "scenario": "expense",
        "account_code": "5000",  # Cost of Goods Sold
    },
}
