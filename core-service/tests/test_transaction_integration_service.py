"""Unit tests for TransactionIntegrationService"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.services.transaction_integration_service import (
    Transaction,
    TransactionIntegrationService,
)


@pytest.fixture
def transaction_service(db_session: Session):
    """Create TransactionIntegrationService instance"""
    return TransactionIntegrationService(db_session)


@pytest.fixture
def sample_transaction():
    """Create a sample transaction for testing"""
    return Transaction(
        id=uuid4(),
        organization_id=uuid4(),
        transaction_type="Quotation",
        customer_id=uuid4(),
        line_items=[
            {
                "item_id": uuid4(),
                "qty": 10,
                "rate": 100.00,
                "amount": 1000.00,
                "is_tax_exempt": False,
            }
        ],
        net_total=Decimal("0.00"),
        total_tax=Decimal("0.00"),
        total_charges=Decimal("0.00"),
        grand_total=Decimal("0.00"),
    )


def test_apply_taxes_and_charges_basic(transaction_service, sample_transaction):
    """Test basic tax and charge application"""
    user_id = uuid4()

    # Apply taxes and charges
    result = transaction_service.apply_taxes_and_charges(sample_transaction, user_id)

    # Verify transaction structure
    assert result.id == sample_transaction.id
    assert result.organization_id == sample_transaction.organization_id
    assert result.net_total == Decimal("1000.00")
    assert isinstance(result.total_tax, Decimal)
    assert isinstance(result.total_charges, Decimal)
    assert isinstance(result.grand_total, Decimal)

    # Verify grand total calculation
    expected_grand_total = result.net_total + result.total_tax + result.total_charges
    assert result.grand_total == expected_grand_total


def test_recalculate_totals(transaction_service, sample_transaction):
    """Test recalculating totals when line items change"""
    # Initial calculation
    result = transaction_service.recalculate_totals(sample_transaction)

    # Verify net total is calculated from line items
    assert result.net_total == Decimal("1000.00")

    # Modify line items
    sample_transaction.line_items[0]["amount"] = 2000.00

    # Recalculate
    result = transaction_service.recalculate_totals(sample_transaction)

    # Verify net total is updated
    assert result.net_total == Decimal("2000.00")


def test_convert_to_line_items(transaction_service):
    """Test conversion of line item dictionaries to LineItem dataclass"""
    line_items_data = [
        {
            "item_id": uuid4(),
            "qty": 5,
            "rate": 200.00,
            "amount": 1000.00,
            "is_tax_exempt": False,
        },
        {
            "item_id": uuid4(),
            "qty": 10,
            "rate": 50.00,
            "amount": 500.00,
            "is_tax_exempt": True,
        },
    ]

    line_items = transaction_service._convert_to_line_items(line_items_data)

    assert len(line_items) == 2
    assert line_items[0].qty == Decimal("5")
    assert line_items[0].rate == Decimal("200.00")
    assert line_items[0].amount == Decimal("1000.00")
    assert line_items[0].is_tax_exempt is False
    assert line_items[1].is_tax_exempt is True


def test_get_transaction_category(transaction_service):
    """Test transaction category determination"""
    assert transaction_service._get_transaction_category("Quotation") == "Sales"
    assert transaction_service._get_transaction_category("Sales_Order") == "Sales"
    assert transaction_service._get_transaction_category("Invoice") == "Sales"
    assert transaction_service._get_transaction_category("Purchase_Order") == "Purchase"
    assert (
        transaction_service._get_transaction_category("Purchase_Receipt") == "Purchase"
    )
    assert transaction_service._get_transaction_category("Unknown") == "Sales"


def test_tax_exempt_customer(transaction_service):
    """Test that tax-exempt customers have zero taxes"""
    transaction = Transaction(
        id=uuid4(),
        organization_id=uuid4(),
        transaction_type="Quotation",
        customer_id=uuid4(),
        line_items=[
            {
                "item_id": uuid4(),
                "qty": 10,
                "rate": 100.00,
                "amount": 1000.00,
                "is_tax_exempt": False,
            }
        ],
        is_customer_tax_exempt=True,
    )

    user_id = uuid4()
    result = transaction_service.apply_taxes_and_charges(transaction, user_id)

    # Tax-exempt customer should have zero taxes
    assert result.total_tax == Decimal("0.00")
    assert result.net_total == Decimal("1000.00")


def test_empty_line_items(transaction_service):
    """Test handling of empty line items"""
    transaction = Transaction(
        id=uuid4(),
        organization_id=uuid4(),
        transaction_type="Quotation",
        customer_id=uuid4(),
        line_items=[],
    )

    user_id = uuid4()
    result = transaction_service.apply_taxes_and_charges(transaction, user_id)

    # Empty line items should result in zero totals
    assert result.net_total == Decimal("0.00")
    assert result.total_tax == Decimal("0.00")
    assert result.total_charges == Decimal("0.00")
    assert result.grand_total == Decimal("0.00")
