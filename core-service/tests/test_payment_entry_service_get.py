"""Test for PaymentEntryService.get_payment_entry() method"""

import pytest
from datetime import datetime, UTC
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.base import PaymentEntryStatus, PaymentSource, PaymentEntryType, PaymentMode
from app.models.customer import Customer
from app.models.payment_entry import PaymentEntry
from app.models.payment_reference import PaymentReference
from app.services.payment_entry_service import PaymentEntryService


def test_get_payment_entry_success(db_session):
    """Test successful retrieval of payment entry"""
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
    
    # Create payment entry directly in database
    payment_entry = PaymentEntry(
        id=uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=customer.id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.BANK_TRANSFER,
        reference_no="UTR123456",
        status=PaymentEntryStatus.DRAFT,
        source=PaymentSource.MANUAL,
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(payment_entry)
    db_session.commit()
    
    # Retrieve payment entry using service
    service = PaymentEntryService(db_session)
    result = service.get_payment_entry(payment_entry.id, org_id)
    
    # Verify response
    assert result.id == payment_entry.id
    assert result.organization_id == org_id
    assert result.payment_type == "Customer_Payment"
    assert result.party_id == customer.id
    assert result.amount == Decimal("1000.00")
    assert result.currency_code == "USD"
    assert result.payment_mode == "Bank_Transfer"
    assert result.reference_no == "UTR123456"
    assert result.status == PaymentEntryStatus.DRAFT.value
    assert result.source == PaymentSource.MANUAL.value
    assert result.unallocated_amount == Decimal("1000.00")
    assert result.created_by == user_id
    assert result.updated_by == user_id


def test_get_payment_entry_with_allocations(db_session):
    """Test retrieval of payment entry with allocations"""
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
    payment_entry = PaymentEntry(
        id=uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=customer.id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        source=PaymentSource.MANUAL,
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(payment_entry)
    db_session.commit()
    
    # Create payment references (allocations)
    invoice_id_1 = uuid4()
    invoice_id_2 = uuid4()
    
    ref1 = PaymentReference(
        id=uuid4(),
        organization_id=org_id,
        payment_id=payment_entry.id,
        invoice_id=invoice_id_1,
        allocated_amount=Decimal("600.00"),
        exchange_rate=Decimal("1.0"),
        allocated_amount_invoice_currency=Decimal("600.00"),
        created_by=user_id,
    )
    ref2 = PaymentReference(
        id=uuid4(),
        organization_id=org_id,
        payment_id=payment_entry.id,
        invoice_id=invoice_id_2,
        allocated_amount=Decimal("300.00"),
        exchange_rate=Decimal("1.0"),
        allocated_amount_invoice_currency=Decimal("300.00"),
        created_by=user_id,
    )
    db_session.add_all([ref1, ref2])
    db_session.commit()
    
    # Retrieve payment entry using service
    service = PaymentEntryService(db_session)
    result = service.get_payment_entry(payment_entry.id, org_id)
    
    # Verify response
    assert result.id == payment_entry.id
    assert result.amount == Decimal("1000.00")
    assert result.unallocated_amount == Decimal("100.00")  # 1000 - 600 - 300
    
    # Verify allocations are included
    assert len(result.payment_references) == 2
    assert result.payment_references[0].allocated_amount == Decimal("600.00")
    assert result.payment_references[1].allocated_amount == Decimal("300.00")


def test_get_payment_entry_not_found(db_session):
    """Test retrieval of non-existent payment entry"""
    org_id = uuid4()
    non_existent_id = uuid4()
    
    service = PaymentEntryService(db_session)
    
    with pytest.raises(ValidationError, match="not found or does not belong to organization"):
        service.get_payment_entry(non_existent_id, org_id)


def test_get_payment_entry_wrong_organization(db_session):
    """Test retrieval of payment entry from different organization"""
    org_id_1 = uuid4()
    org_id_2 = uuid4()
    user_id = uuid4()
    
    # Create test customer in org_id_1
    customer = Customer(
        id=uuid4(),
        organization_id=org_id_1,
        customer_name="Test Customer",
        customer_code="CUST001",
        email="test@example.com",
    )
    db_session.add(customer)
    db_session.commit()
    
    # Create payment entry in org_id_1
    payment_entry = PaymentEntry(
        id=uuid4(),
        organization_id=org_id_1,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=customer.id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        source=PaymentSource.MANUAL,
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(payment_entry)
    db_session.commit()
    
    # Try to retrieve from org_id_2
    service = PaymentEntryService(db_session)
    
    with pytest.raises(ValidationError, match="not found or does not belong to organization"):
        service.get_payment_entry(payment_entry.id, org_id_2)
