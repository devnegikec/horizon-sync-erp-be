"""Tests for PaymentEntryService.list_payment_entries() method"""

import pytest
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from uuid import uuid4

from app.models.base import PaymentEntryStatus, PaymentMode, PaymentEntryType
from app.models.customer import Customer
from app.schemas.payment_entry import PaymentFilters, PaymentEntryCreate
from app.services.payment_entry_service import PaymentEntryService


def test_list_payment_entries_basic(db_session):
    """Test basic listing of payment entries"""
    service = PaymentEntryService(db_session)
    org_id = uuid4()
    user_id = uuid4()
    
    # Create test customer
    customer = Customer(
        id=uuid4(),
        organization_id=org_id,
        customer_name="Test Customer",
        customer_code="CUST001",
        email="test@example.com",
    )
    db_session.add(customer)
    db_session.commit()
    
    # Create a few payment entries
    payment_data_1 = PaymentEntryCreate(
        payment_type="Customer_Payment",
        party_id=customer.id,
        amount=Decimal("100.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode="Cash",
    )
    
    payment_data_2 = PaymentEntryCreate(
        payment_type="Customer_Payment",
        party_id=customer.id,
        amount=Decimal("200.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC) - timedelta(days=1),
        payment_mode="Bank_Transfer",
        reference_no="UTR123456",
    )
    
    service.create_payment_entry(payment_data_1, org_id, user_id)
    service.create_payment_entry(payment_data_2, org_id, user_id)
    
    # List all payment entries
    filters = PaymentFilters()
    result = service.list_payment_entries(
        filters=filters,
        organization_id=org_id,
        page=1,
        page_size=50,
    )
    
    # Verify results
    assert len(result.payment_entries) == 2
    assert result.pagination.total == 2
    assert result.pagination.page == 1
    assert result.pagination.page_size == 50
    assert result.pagination.total_pages == 1
    assert result.pagination.has_next is False
    assert result.pagination.has_prev is False


def test_list_payment_entries_with_status_filter(db_session):
    """Test listing payment entries with status filter"""
    service = PaymentEntryService(db_session)
    org_id = uuid4()
    user_id = uuid4()
    
    # Create test customer
    customer = Customer(
        id=uuid4(),
        organization_id=org_id,
        customer_name="Test Customer",
        customer_code="CUST001",
        email="test@example.com",
    )
    db_session.add(customer)
    db_session.commit()
    
    # Create payment entry
    payment_data = PaymentEntryCreate(
        payment_type="Customer_Payment",
        party_id=customer.id,
        amount=Decimal("100.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode="Cash",
    )
    
    service.create_payment_entry(payment_data, org_id, user_id)
    
    # List with Draft status filter
    filters = PaymentFilters(status="Draft")
    result = service.list_payment_entries(
        filters=filters,
        organization_id=org_id,
    )
    
    assert len(result.payment_entries) >= 1
    assert all(entry.status == "Draft" for entry in result.payment_entries)


def test_list_payment_entries_pagination(db_session):
    """Test pagination of payment entries"""
    service = PaymentEntryService(db_session)
    org_id = uuid4()
    user_id = uuid4()
    
    # Create test customer
    customer = Customer(
        id=uuid4(),
        organization_id=org_id,
        customer_name="Test Customer",
        customer_code="CUST001",
        email="test@example.com",
    )
    db_session.add(customer)
    db_session.commit()
    
    # Create multiple payment entries
    for i in range(5):
        payment_data = PaymentEntryCreate(
            payment_type="Customer_Payment",
            party_id=customer.id,
            amount=Decimal(f"{100 + i}.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC) - timedelta(days=i),
            payment_mode="Cash",
        )
        service.create_payment_entry(payment_data, org_id, user_id)
    
    # Get first page with page_size=2
    filters = PaymentFilters()
    result_page1 = service.list_payment_entries(
        filters=filters,
        organization_id=org_id,
        page=1,
        page_size=2,
    )
    
    assert len(result_page1.payment_entries) == 2
    assert result_page1.pagination.page == 1
    assert result_page1.pagination.total == 5
    assert result_page1.pagination.has_next is True
    assert result_page1.pagination.has_prev is False
    
    # Get second page
    result_page2 = service.list_payment_entries(
        filters=filters,
        organization_id=org_id,
        page=2,
        page_size=2,
    )
    
    assert len(result_page2.payment_entries) == 2
    assert result_page2.pagination.page == 2
    assert result_page2.pagination.has_prev is True


def test_list_payment_entries_invalid_status(db_session):
    """Test listing with invalid status filter"""
    service = PaymentEntryService(db_session)
    org_id = uuid4()
    
    filters = PaymentFilters(status="InvalidStatus")
    
    with pytest.raises(Exception) as exc_info:
        service.list_payment_entries(
            filters=filters,
            organization_id=org_id,
        )
    
    assert "Invalid status" in str(exc_info.value)


def test_list_payment_entries_invalid_payment_mode(db_session):
    """Test listing with invalid payment_mode filter"""
    service = PaymentEntryService(db_session)
    org_id = uuid4()
    
    filters = PaymentFilters(payment_mode="InvalidMode")
    
    with pytest.raises(Exception) as exc_info:
        service.list_payment_entries(
            filters=filters,
            organization_id=org_id,
        )
    
    assert "Invalid payment_mode" in str(exc_info.value)
