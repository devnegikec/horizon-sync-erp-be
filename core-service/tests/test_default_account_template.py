"""Tests for default account template and mappings configuration"""

import pytest

from app.services.default_account_template import (
    AccountTemplate,
    get_default_account_structure,
    DEFAULT_MAPPINGS,
)
from app.models.base import AccountType


class TestDefaultAccountStructure:
    """Tests for default account structure template"""

    def test_get_default_account_structure_returns_list(self):
        """Test that get_default_account_structure returns a list"""
        structure = get_default_account_structure()
        assert isinstance(structure, list)
        assert len(structure) > 0

    def test_all_items_are_account_templates(self):
        """Test that all items in structure are AccountTemplate instances"""
        structure = get_default_account_structure()
        for item in structure:
            assert isinstance(item, AccountTemplate)

    def test_includes_all_account_types(self):
        """Test that structure includes all five account types"""
        structure = get_default_account_structure()
        account_types = {account.account_type for account in structure}
        
        assert AccountType.ASSET in account_types
        assert AccountType.LIABILITY in account_types
        assert AccountType.EQUITY in account_types
        assert AccountType.REVENUE in account_types
        assert AccountType.EXPENSE in account_types

    def test_account_codes_are_unique(self):
        """Test that all account codes are unique"""
        structure = get_default_account_structure()
        account_codes = [account.account_code for account in structure]
        
        assert len(account_codes) == len(set(account_codes))

    def test_function_is_cached(self):
        """Test that function uses lru_cache"""
        result1 = get_default_account_structure()
        result2 = get_default_account_structure()
        
        # Should return the same object due to caching
        assert result1 is result2


class TestDefaultMappings:
    """Tests for DEFAULT_MAPPINGS configuration"""

    def test_default_mappings_is_dict(self):
        """Test that DEFAULT_MAPPINGS is a dictionary"""
        assert isinstance(DEFAULT_MAPPINGS, dict)

    def test_includes_required_mappings(self):
        """Test that all required mappings are present"""
        required_keys = [
            "payment_cash",
            "payment_bank",
            "accounts_receivable",
            "accounts_payable",
            "sales_revenue",
            "purchase_expense",
        ]
        
        for key in required_keys:
            assert key in DEFAULT_MAPPINGS, f"Missing required mapping: {key}"

    def test_payment_cash_mapping(self):
        """Test payment_cash mapping configuration"""
        mapping = DEFAULT_MAPPINGS["payment_cash"]
        
        assert mapping["transaction_type"] == "payment"
        assert mapping["scenario"] == "cash"
        assert mapping["account_code"] == "1010"  # Cash

    def test_payment_bank_mapping(self):
        """Test payment_bank mapping configuration"""
        mapping = DEFAULT_MAPPINGS["payment_bank"]
        
        assert mapping["transaction_type"] == "payment"
        assert mapping["scenario"] == "bank"
        assert mapping["account_code"] == "1020"  # Bank Accounts

    def test_accounts_receivable_mapping(self):
        """Test accounts_receivable mapping configuration"""
        mapping = DEFAULT_MAPPINGS["accounts_receivable"]
        
        assert mapping["transaction_type"] == "sales_invoice"
        assert mapping["scenario"] == "receivable"
        assert mapping["account_code"] == "1200"  # Accounts Receivable

    def test_accounts_payable_mapping(self):
        """Test accounts_payable mapping configuration"""
        mapping = DEFAULT_MAPPINGS["accounts_payable"]
        
        assert mapping["transaction_type"] == "purchase_invoice"
        assert mapping["scenario"] == "payable"
        assert mapping["account_code"] == "2000"  # Accounts Payable

    def test_sales_revenue_mapping(self):
        """Test sales_revenue mapping configuration"""
        mapping = DEFAULT_MAPPINGS["sales_revenue"]
        
        assert mapping["transaction_type"] == "sales_invoice"
        assert mapping["scenario"] == "revenue"
        assert mapping["account_code"] == "4000"  # Sales Revenue

    def test_purchase_expense_mapping(self):
        """Test purchase_expense mapping configuration"""
        mapping = DEFAULT_MAPPINGS["purchase_expense"]
        
        assert mapping["transaction_type"] == "purchase_invoice"
        assert mapping["scenario"] == "expense"
        assert mapping["account_code"] == "5000"  # Cost of Goods Sold

    def test_all_mappings_have_required_fields(self):
        """Test that all mappings have required fields"""
        required_fields = ["transaction_type", "scenario", "account_code"]
        
        for key, mapping in DEFAULT_MAPPINGS.items():
            for field in required_fields:
                assert field in mapping, f"Mapping {key} missing field: {field}"

    def test_mapped_account_codes_exist_in_structure(self):
        """Test that all mapped account codes exist in default structure"""
        structure = get_default_account_structure()
        structure_codes = {account.account_code for account in structure}
        
        for key, mapping in DEFAULT_MAPPINGS.items():
            account_code = mapping["account_code"]
            assert account_code in structure_codes, (
                f"Mapping {key} references non-existent account code: {account_code}"
            )

    def test_mapped_accounts_are_posting_accounts(self):
        """Test that all mapped accounts are posting accounts (not groups)"""
        structure = get_default_account_structure()
        accounts_by_code = {account.account_code: account for account in structure}
        
        for key, mapping in DEFAULT_MAPPINGS.items():
            account_code = mapping["account_code"]
            account = accounts_by_code[account_code]
            
            assert account.is_posting_account, (
                f"Mapping {key} references a non-posting account: {account_code}"
            )
