"""Simple unit tests for ChargeCalculationEngine without full app import"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uuid
from decimal import Decimal
from unittest.mock import Mock

from app.services.charge_calculation_engine import (
    ChargeCalculationEngine,
    ChargeContext,
)


def test_calculate_single_charge_fixed_amount():
    """Test calculating a fixed amount charge"""
    mock_db = Mock()
    engine = ChargeCalculationEngine(mock_db)

    # Create a mock charge template
    template = Mock()
    template.id = uuid.uuid4()
    template.organization_id = uuid.uuid4()
    template.template_code = "SHIP_FIXED"
    template.template_name = "Fixed Shipping"
    template.charge_type = "Shipping"
    template.calculation_method = "FIXED"
    template.fixed_amount = Decimal("50.00")
    template.account_head_id = uuid.uuid4()
    template.is_active = True

    base_amount = Decimal("1000.00")
    result = engine.calculate_single_charge(template, base_amount)

    assert result.charge_amount == Decimal("50.00")
    assert result.charge_type == "Shipping"
    assert result.calculation_method == "FIXED"
    assert result.is_auto_calculated is True


def test_calculate_single_charge_percentage_net_total():
    """Test calculating a percentage charge based on net total"""
    mock_db = Mock()
    engine = ChargeCalculationEngine(mock_db)

    # Create a mock percentage charge template
    template = Mock()
    template.id = uuid.uuid4()
    template.template_name = "Percentage Shipping"
    template.charge_type = "Shipping"
    template.calculation_method = "PERCENTAGE"
    template.percentage_rate = Decimal("5.00")
    template.base_on = "Net_Total"
    template.account_head_id = uuid.uuid4()

    base_amount = Decimal("1000.00")
    result = engine.calculate_single_charge(template, base_amount)

    # 5% of 1000 = 50.00
    assert result.charge_amount == Decimal("50.00")
    assert result.charge_type == "Shipping"
    assert result.calculation_method == "PERCENTAGE"


def test_calculate_single_charge_percentage_grand_total():
    """Test calculating a percentage charge based on grand total"""
    mock_db = Mock()
    engine = ChargeCalculationEngine(mock_db)

    # Create a mock percentage charge template
    template = Mock()
    template.id = uuid.uuid4()
    template.template_name = "Handling Fee"
    template.charge_type = "Handling"
    template.calculation_method = "PERCENTAGE"
    template.percentage_rate = Decimal("2.50")
    template.base_on = "Grand_Total"
    template.account_head_id = uuid.uuid4()

    # Grand total = net_total + tax = 1000 + 180 = 1180
    grand_total = Decimal("1180.00")
    result = engine.calculate_single_charge(template, grand_total)

    # 2.5% of 1180 = 29.50
    assert result.charge_amount == Decimal("29.50")
    assert result.charge_type == "Handling"


def test_calculate_charges_no_applicable_templates():
    """Test calculating charges when no templates are applicable"""
    mock_db = Mock()
    engine = ChargeCalculationEngine(mock_db)

    # Mock the repository to return empty list
    engine.charge_template_repo.get_applicable_charges = Mock(return_value=[])

    context = ChargeContext(
        organization_id=uuid.uuid4(),
        transaction_type="Sales_Order",
        net_total=Decimal("1000.00"),
    )

    result = engine.calculate_charges(
        context=context,
        net_total=Decimal("1000.00"),
        total_tax=Decimal("180.00"),
    )

    assert result.total_charges == Decimal("0.00")
    assert len(result.charge_breakdown) == 0


def test_calculate_charges_with_fixed_charge():
    """Test calculating a single fixed charge"""
    mock_db = Mock()
    engine = ChargeCalculationEngine(mock_db)

    # Create mock template
    template = Mock()
    template.id = uuid.uuid4()
    template.template_name = "Fixed Shipping"
    template.charge_type = "Shipping"
    template.calculation_method = "FIXED"
    template.fixed_amount = Decimal("50.00")
    template.account_head_id = uuid.uuid4()

    # Mock the repository to return the template
    engine.charge_template_repo.get_applicable_charges = Mock(return_value=[template])

    context = ChargeContext(
        organization_id=uuid.uuid4(),
        transaction_type="Sales_Order",
        net_total=Decimal("1000.00"),
    )

    result = engine.calculate_charges(
        context=context,
        net_total=Decimal("1000.00"),
        total_tax=Decimal("180.00"),
    )

    assert result.total_charges == Decimal("50.00")
    assert len(result.charge_breakdown) == 1
    assert result.charge_breakdown[0].charge_amount == Decimal("50.00")


def test_calculate_charges_with_percentage_on_net_total():
    """Test calculating percentage charge based on net total"""
    mock_db = Mock()
    engine = ChargeCalculationEngine(mock_db)

    # Create mock template
    template = Mock()
    template.id = uuid.uuid4()
    template.template_name = "Handling Fee"
    template.charge_type = "Handling"
    template.calculation_method = "PERCENTAGE"
    template.percentage_rate = Decimal("2.00")
    template.base_on = "Net_Total"
    template.account_head_id = uuid.uuid4()

    # Mock the repository
    engine.charge_template_repo.get_applicable_charges = Mock(return_value=[template])

    context = ChargeContext(
        organization_id=uuid.uuid4(),
        transaction_type="Sales_Order",
        net_total=Decimal("1000.00"),
    )

    result = engine.calculate_charges(
        context=context,
        net_total=Decimal("1000.00"),
        total_tax=Decimal("180.00"),
    )

    # 2% of 1000 = 20.00
    assert result.total_charges == Decimal("20.00")
    assert len(result.charge_breakdown) == 1


def test_calculate_charges_with_percentage_on_grand_total():
    """Test calculating percentage charge based on grand total (net + tax)"""
    mock_db = Mock()
    engine = ChargeCalculationEngine(mock_db)

    # Create mock template
    template = Mock()
    template.id = uuid.uuid4()
    template.template_name = "Insurance Fee"
    template.charge_type = "Insurance"
    template.calculation_method = "PERCENTAGE"
    template.percentage_rate = Decimal("1.00")
    template.base_on = "Grand_Total"
    template.account_head_id = uuid.uuid4()

    # Mock the repository
    engine.charge_template_repo.get_applicable_charges = Mock(return_value=[template])

    context = ChargeContext(
        organization_id=uuid.uuid4(),
        transaction_type="Sales_Order",
        net_total=Decimal("1000.00"),
    )

    result = engine.calculate_charges(
        context=context,
        net_total=Decimal("1000.00"),
        total_tax=Decimal("180.00"),
    )

    # 1% of (1000 + 180) = 1% of 1180 = 11.80
    assert result.total_charges == Decimal("11.80")
    assert len(result.charge_breakdown) == 1
    assert result.charge_breakdown[0].charge_amount == Decimal("11.80")


def test_calculate_charges_with_multiple_charges():
    """Test calculating multiple charges"""
    mock_db = Mock()
    engine = ChargeCalculationEngine(mock_db)

    # Create mock templates
    shipping_template = Mock()
    shipping_template.id = uuid.uuid4()
    shipping_template.template_name = "Fixed Shipping"
    shipping_template.charge_type = "Shipping"
    shipping_template.calculation_method = "FIXED"
    shipping_template.fixed_amount = Decimal("50.00")
    shipping_template.account_head_id = uuid.uuid4()

    handling_template = Mock()
    handling_template.id = uuid.uuid4()
    handling_template.template_name = "Handling Fee"
    handling_template.charge_type = "Handling"
    handling_template.calculation_method = "PERCENTAGE"
    handling_template.percentage_rate = Decimal("2.00")
    handling_template.base_on = "Net_Total"
    handling_template.account_head_id = uuid.uuid4()

    # Mock the repository to return both templates
    engine.charge_template_repo.get_applicable_charges = Mock(
        return_value=[shipping_template, handling_template]
    )

    context = ChargeContext(
        organization_id=uuid.uuid4(),
        transaction_type="Sales_Order",
        net_total=Decimal("1000.00"),
    )

    result = engine.calculate_charges(
        context=context,
        net_total=Decimal("1000.00"),
        total_tax=Decimal("180.00"),
    )

    # Should have 2 charges: 50.00 (fixed) + 20.00 (2% of 1000) = 70.00
    assert result.total_charges == Decimal("70.00")
    assert len(result.charge_breakdown) == 2


if __name__ == "__main__":
    # Run tests
    test_calculate_single_charge_fixed_amount()
    print("✓ test_calculate_single_charge_fixed_amount passed")

    test_calculate_single_charge_percentage_net_total()
    print("✓ test_calculate_single_charge_percentage_net_total passed")

    test_calculate_single_charge_percentage_grand_total()
    print("✓ test_calculate_single_charge_percentage_grand_total passed")

    test_calculate_charges_no_applicable_templates()
    print("✓ test_calculate_charges_no_applicable_templates passed")

    test_calculate_charges_with_fixed_charge()
    print("✓ test_calculate_charges_with_fixed_charge passed")

    test_calculate_charges_with_percentage_on_net_total()
    print("✓ test_calculate_charges_with_percentage_on_net_total passed")

    test_calculate_charges_with_percentage_on_grand_total()
    print("✓ test_calculate_charges_with_percentage_on_grand_total passed")

    test_calculate_charges_with_multiple_charges()
    print("✓ test_calculate_charges_with_multiple_charges passed")

    print("\nAll tests passed!")
