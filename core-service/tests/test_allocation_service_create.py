"""Tests for AllocationService.create_allocation() method"""

import uuid
from decimal import Decimal
from datetime import datetime, UTC

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.base import PaymentEntryStatus, PaymentEntryType, PaymentMode
from app.models.payment_entry import PaymentEntry
from app.models.invoice import Invoice
from app.services.allocation_service import AllocationService


@pytest.fixture
def test_organization_id():
    """Test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return uuid.uuid4()


def test_create_allocation_success(db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID):
    """Test successful payment allocation to invoice"""
    # Create a payment entry
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(payment)
    
    # Create an invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-001",
        invoice_type="sales",
        party_id=payment.party_id,  # Same party as payment
        party_type="customer",
        grand_total=Decimal("500.00"),
        outstanding_amount=Decimal("500.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(invoice)
    db_session.commit()
    
    # Create allocation
    service = AllocationService(db_session)
    allocation = service.create_allocation(
        payment_id=payment.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("500.00"),
        organization_id=test_organization_id,
        user_id=test_user_id,
    )
    
    # Verify allocation was created
    assert allocation is not None
    assert allocation.payment_id == payment.id
    assert allocation.invoice_id == invoice.id
    assert allocation.allocated_amount == Decimal("500.00")
    assert allocation.exchange_rate == Decimal("1.0")
    assert allocation.allocated_amount_invoice_currency == Decimal("500.00")


def test_create_allocation_payment_not_draft(db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID):
    """Test that allocation fails when payment is not in Draft status"""
    # Create a confirmed payment entry
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.CONFIRMED,  # Not Draft
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(payment)
    
    # Create an invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-002",
        invoice_type="sales",
        party_id=payment.party_id,
        party_type="customer",
        grand_total=Decimal("500.00"),
        outstanding_amount=Decimal("500.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(invoice)
    db_session.commit()
    
    # Try to create allocation - should fail
    service = AllocationService(db_session)
    with pytest.raises(ValidationError, match="Payment must be in Draft status"):
        service.create_allocation(
            payment_id=payment.id,
            invoice_id=invoice.id,
            allocated_amount=Decimal("500.00"),
            organization_id=test_organization_id,
            user_id=test_user_id,
        )


def test_create_allocation_exceeds_unallocated_amount(db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID):
    """Test that allocation fails when amount exceeds payment unallocated amount"""
    # Create a payment entry
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(payment)
    
    # Create an invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-003",
        invoice_type="sales",
        party_id=payment.party_id,
        party_type="customer",
        grand_total=Decimal("2000.00"),
        outstanding_amount=Decimal("2000.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(invoice)
    db_session.commit()
    
    # Try to allocate more than payment amount - should fail
    service = AllocationService(db_session)
    with pytest.raises(ValidationError, match="exceeds payment unallocated amount"):
        service.create_allocation(
            payment_id=payment.id,
            invoice_id=invoice.id,
            allocated_amount=Decimal("1500.00"),  # More than payment amount
            organization_id=test_organization_id,
            user_id=test_user_id,
        )


def test_create_allocation_different_party(db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID):
    """Test that allocation fails when invoice belongs to different party"""
    # Create a payment entry
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(payment)
    
    # Create an invoice with different party
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-004",
        invoice_type="sales",
        party_id=uuid.uuid4(),  # Different party
        party_type="customer",
        grand_total=Decimal("500.00"),
        outstanding_amount=Decimal("500.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(invoice)
    db_session.commit()
    
    # Try to create allocation - should fail
    service = AllocationService(db_session)
    with pytest.raises(ValidationError, match="does not match payment party"):
        service.create_allocation(
            payment_id=payment.id,
            invoice_id=invoice.id,
            allocated_amount=Decimal("500.00"),
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
