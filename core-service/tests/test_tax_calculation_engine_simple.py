"""Simple unit tests for TaxCalculationEngine without full app import"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import uuid
from decimal import Decimal
from unittest.mock import Mock, MagicMock

from app.services.tax_calculation_engine import (
    LineItem,
    TaxCalculationEngine,
    TaxContext,
    TaxBreakdownEntry,
)


def test_calculate_tax_amount():
    """Test basic tax amount calculation"""
    # Create a mock db session
    mock_db = Mock()
    engine = TaxCalculationEngine(mock_db)
    
    amount = Decimal("1000.00")
    tax_rate = Decimal("18.00")
    
    tax_amount = engine._calculate_tax_amount(amount, tax_rate)
    
    assert tax_amount == Decimal("180.00")


def test_calculate_tax_amount_with_rounding():
    """Test tax amount calculation with rounding"""
    mock_db = Mock()
    engine = TaxCalculationEngine(mock_db)
    
    amount = Decimal("1000.00")
    tax_rate = Decimal("9.50")
    
    tax_amount = engine._calculate_tax_amount(amount, tax_rate)
    
    # 1000 * 9.5 / 100 = 95.00
    assert tax_amount == Decimal("95.00")


def test_apply_compound_taxes():
    """Test applying compound taxes on base amount plus non-compound taxes"""
    mock_db = Mock()
    engine = TaxCalculationEngine(mock_db)
    
    base_amount = Decimal("1000.00")
    template_id = uuid.uuid4()
    account_head_id = uuid.uuid4()
    
    # Create mock non-compound tax entries
    non_compound_taxes = [
        TaxBreakdownEntry(
            tax_template_id=template_id,
            tax_rule_id=uuid.uuid4(),
            tax_type="CGST",
            tax_rate=Decimal("9.00"),
            taxable_amount=base_amount,
            tax_amount=Decimal("90.00"),
            is_compound=False,
            sequence=1,
            account_head_id=account_head_id,
        ),
        TaxBreakdownEntry(
            tax_template_id=template_id,
            tax_rule_id=uuid.uuid4(),
            tax_type="SGST",
            tax_rate=Decimal("9.00"),
            taxable_amount=base_amount,
            tax_amount=Decimal("90.00"),
            is_compound=False,
            sequence=2,
            account_head_id=account_head_id,
        ),
    ]
    
    # Create mock compound tax rule
    compound_rule = Mock()
    compound_rule.id = uuid.uuid4()
    compound_rule.tax_type = "CESS"
    compound_rule.tax_rate = Decimal("1.00")
    compound_rule.account_head_id = account_head_id
    compound_rule.sequence = 3
    
    compound_entries = engine.apply_compound_taxes(
        base_amount, non_compound_taxes, [compound_rule], template_id
    )
    
    assert len(compound_entries) == 1
    assert compound_entries[0].tax_type == "CESS"
    # Compound base = 1000 + 90 + 90 = 1180
    assert compound_entries[0].taxable_amount == Decimal("1180.00")
    # Tax = 1180 * 1 / 100 = 11.80
    assert compound_entries[0].tax_amount == Decimal("11.80")
    assert compound_entries[0].is_compound is True


def test_calculate_taxes_with_tax_exempt_customer():
    """Test that no taxes are calculated for tax-exempt customers"""
    mock_db = Mock()
    engine = TaxCalculationEngine(mock_db)
    
    line_items = [
        LineItem(
            item_id=uuid.uuid4(),
            qty=Decimal("10"),
            rate=Decimal("100.00"),
            amount=Decimal("1000.00"),
            is_tax_exempt=False,
        )
    ]
    
    context = TaxContext(
        organization_id=uuid.uuid4(),
        transaction_type="Sales",
        is_customer_tax_exempt=True,
    )
    
    result = engine.calculate_taxes(line_items, context)
    
    assert result.net_total == Decimal("1000.00")
    assert result.total_tax == Decimal("0.00")
    assert len(result.tax_breakdown) == 0
    assert result.taxes_by_type == {}


def test_calculate_taxes_all_items_exempt():
    """Test calculating taxes when all line items are tax-exempt"""
    mock_db = Mock()
    engine = TaxCalculationEngine(mock_db)
    
    line_items = [
        LineItem(
            item_id=uuid.uuid4(),
            qty=Decimal("10"),
            rate=Decimal("100.00"),
            amount=Decimal("1000.00"),
            is_tax_exempt=True,
        ),
        LineItem(
            item_id=uuid.uuid4(),
            qty=Decimal("5"),
            rate=Decimal("50.00"),
            amount=Decimal("250.00"),
            is_tax_exempt=True,
        ),
    ]
    
    context = TaxContext(
        organization_id=uuid.uuid4(),
        transaction_type="Sales",
        is_customer_tax_exempt=False,
    )
    
    result = engine.calculate_taxes(line_items, context)
    
    assert result.net_total == Decimal("1250.00")
    assert result.total_tax == Decimal("0.00")
    assert len(result.tax_breakdown) == 0


def test_calculate_taxes_empty_line_items():
    """Test calculating taxes with empty line items"""
    mock_db = Mock()
    engine = TaxCalculationEngine(mock_db)
    
    line_items = []
    
    context = TaxContext(
        organization_id=uuid.uuid4(),
        transaction_type="Sales",
        is_customer_tax_exempt=False,
    )
    
    result = engine.calculate_taxes(line_items, context)
    
    assert result.net_total == Decimal("0.00")
    assert result.total_tax == Decimal("0.00")
    assert len(result.tax_breakdown) == 0


if __name__ == "__main__":
    # Run tests
    test_calculate_tax_amount()
    print("✓ test_calculate_tax_amount passed")
    
    test_calculate_tax_amount_with_rounding()
    print("✓ test_calculate_tax_amount_with_rounding passed")
    
    test_apply_compound_taxes()
    print("✓ test_apply_compound_taxes passed")
    
    test_calculate_taxes_with_tax_exempt_customer()
    print("✓ test_calculate_taxes_with_tax_exempt_customer passed")
    
    test_calculate_taxes_all_items_exempt()
    print("✓ test_calculate_taxes_all_items_exempt passed")
    
    test_calculate_taxes_empty_line_items()
    print("✓ test_calculate_taxes_empty_line_items passed")
    
    print("\nAll tests passed!")
