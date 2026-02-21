"""Tests for AllocationService.get_payment_allocations() method"""

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


def test_get_payment_allocations_success(db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID):
    """Test successful retrieval of payment allocations with invoice details"""
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
    
    # Create two invoices
    invoice1 = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-001",
        invoice_type="sales",
        party_id=payment.party_id,
        party_type="customer",
        posting_date=datetime.now(UTC),
        grand_total=Decimal("500.00"),
        outstanding_amount=Decimal("500.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(invoice1)
    
    invoice2 = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-002",
        invoice_type="sales",
        party_id=payment.party_id,
        party_type="customer",
        posting_date=datetime.now(UTC),
        grand_total=Decimal("300.00"),
        outstanding_amount=Decimal("300.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(invoice2)
    db_session.commit()
    
    # Create allocations
    service = AllocationService(db_session)
    service.create_allocation(
        payment_id=payment.id,
        invoice_id=invoice1.id,
        allocated_amount=Decimal("500.00"),
        organization_id=test_organization_id,
        user_id=test_user_id,
    )
    service.create_allocation(
        payment_id=payment.id,
        invoice_id=invoice2.id,
        allocated_amount=Decimal("300.00"),
        organization_id=test_organization_id,
        user_id=test_user_id,
    )
    
    # Get payment allocations
    allocations = service.get_payment_allocations(
        payment_id=payment.id,
        organization_id=test_organization_id,
    )
    
    # Verify allocations were retrieved
    assert len(allocations) == 2
    
    # Verify first allocation
    alloc1 = next(a for a in allocations if a.invoice_id == invoice1.id)
    assert alloc1.payment_id == payment.id
    assert alloc1.allocated_amount == Decimal("500.00")
    assert alloc1.invoice_no == "INV-001"
    assert alloc1.invoice_amount == Decimal("500.00")
    assert alloc1.invoice_outstanding_balance == Decimal("500.00")
    assert alloc1.invoice_date is not None
    
    # Verify second allocation
    alloc2 = next(a for a in allocations if a.invoice_id == invoice2.id)
    assert alloc2.payment_id == payment.id
    assert alloc2.allocated_amount == Decimal("300.00")
    assert alloc2.invoice_no == "INV-002"
    assert alloc2.invoice_amount == Decimal("300.00")
    assert alloc2.invoice_outstanding_balance == Decimal("300.00")
    assert alloc2.invoice_date is not None


def test_get_payment_allocations_empty(db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID):
    """Test retrieval of payment allocations when no allocations exist"""
    # Create a payment entry with no allocations
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
    db_session.commit()
    
    # Get payment allocations
    service = AllocationService(db_session)
    allocations = service.get_payment_allocations(
        payment_id=payment.id,
        organization_id=test_organization_id,
    )
    
    # Verify no allocations returned
    assert len(allocations) == 0


def test_get_payment_allocations_payment_not_found(db_session: Session, test_organization_id: uuid.UUID):
    """Test that get_payment_allocations fails when payment not found"""
    # Try to get allocations for non-existent payment
    service = AllocationService(db_session)
    with pytest.raises(ValidationError, match="Payment with ID .* not found"):
        service.get_payment_allocations(
            payment_id=uuid.uuid4(),
            organization_id=test_organization_id,
        )


def test_get_payment_allocations_multi_tenancy(db_session: Session, test_user_id: uuid.UUID):
    """Test that get_payment_allocations respects multi-tenancy isolation"""
    org1_id = uuid.uuid4()
    org2_id = uuid.uuid4()
    
    # Create payment in org1
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org1_id,
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
    db_session.commit()
    
    # Try to get allocations from org2 - should fail
    service = AllocationService(db_session)
    with pytest.raises(ValidationError, match="Payment with ID .* not found"):
        service.get_payment_allocations(
            payment_id=payment.id,
            organization_id=org2_id,
        )


def test_get_invoice_allocations_success(db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID):
    """Test successful retrieval of invoice allocations with payment details"""
    # Create an invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-001",
        invoice_type="sales",
        party_id=uuid.uuid4(),
        party_type="customer",
        posting_date=datetime.now(UTC),
        grand_total=Decimal("1000.00"),
        outstanding_amount=Decimal("1000.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(invoice)
    
    # Create two payment entries
    payment1 = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=invoice.party_id,
        amount=Decimal("600.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        receipt_number="RCP-2024-001",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(payment1)
    
    payment2 = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=invoice.party_id,
        amount=Decimal("400.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.BANK_TRANSFER,
        status=PaymentEntryStatus.CONFIRMED,
        receipt_number="RCP-2024-002",
        reference_no="UTR123456",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(payment2)
    db_session.commit()
    
    # Create allocations
    service = AllocationService(db_session)
    service.create_allocation(
        payment_id=payment1.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("600.00"),
        organization_id=test_organization_id,
        user_id=test_user_id,
    )
    
    # For payment2, we need to set it back to DRAFT to allocate
    payment2.status = PaymentEntryStatus.DRAFT
    db_session.commit()
    
    service.create_allocation(
        payment_id=payment2.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("400.00"),
        organization_id=test_organization_id,
        user_id=test_user_id,
    )
    
    # Get invoice allocations
    allocations = service.get_invoice_allocations(
        invoice_id=invoice.id,
        organization_id=test_organization_id,
    )
    
    # Verify allocations were retrieved
    assert len(allocations) == 2
    
    # Verify first allocation with payment details
    alloc1 = next(a for a in allocations if a.payment_id == payment1.id)
    assert alloc1.invoice_id == invoice.id
    assert alloc1.allocated_amount == Decimal("600.00")
    assert alloc1.payment_no == "RCP-2024-001"
    assert alloc1.payment_amount == Decimal("600.00")
    assert alloc1.payment_mode == "Cash"
    assert alloc1.payment_status == "Draft"
    assert alloc1.payment_currency == "USD"
    assert alloc1.payment_date is not None
    
    # Verify second allocation with payment details
    alloc2 = next(a for a in allocations if a.payment_id == payment2.id)
    assert alloc2.invoice_id == invoice.id
    assert alloc2.allocated_amount == Decimal("400.00")
    assert alloc2.payment_no == "RCP-2024-002"
    assert alloc2.payment_amount == Decimal("400.00")
    assert alloc2.payment_mode == "Bank_Transfer"
    assert alloc2.payment_status == "Draft"  # We set it back to Draft
    assert alloc2.payment_currency == "USD"
    assert alloc2.payment_date is not None


def test_get_invoice_allocations_empty(db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID):
    """Test retrieval of invoice allocations when no allocations exist"""
    # Create an invoice with no allocations
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-001",
        invoice_type="sales",
        party_id=uuid.uuid4(),
        party_type="customer",
        posting_date=datetime.now(UTC),
        grand_total=Decimal("1000.00"),
        outstanding_amount=Decimal("1000.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(invoice)
    db_session.commit()
    
    # Get invoice allocations
    service = AllocationService(db_session)
    allocations = service.get_invoice_allocations(
        invoice_id=invoice.id,
        organization_id=test_organization_id,
    )
    
    # Verify no allocations returned
    assert len(allocations) == 0


def test_get_invoice_allocations_invoice_not_found(db_session: Session, test_organization_id: uuid.UUID):
    """Test that get_invoice_allocations fails when invoice not found"""
    # Try to get allocations for non-existent invoice
    service = AllocationService(db_session)
    with pytest.raises(ValidationError, match="Invoice with ID .* not found"):
        service.get_invoice_allocations(
            invoice_id=uuid.uuid4(),
            organization_id=test_organization_id,
        )


def test_get_invoice_allocations_multi_tenancy(db_session: Session, test_user_id: uuid.UUID):
    """Test that get_invoice_allocations respects multi-tenancy isolation"""
    org1_id = uuid.uuid4()
    org2_id = uuid.uuid4()
    
    # Create invoice in org1
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org1_id,
        invoice_no="INV-001",
        invoice_type="sales",
        party_id=uuid.uuid4(),
        party_type="customer",
        posting_date=datetime.now(UTC),
        grand_total=Decimal("1000.00"),
        outstanding_amount=Decimal("1000.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(invoice)
    db_session.commit()
    
    # Try to get allocations from org2 - should fail
    service = AllocationService(db_session)
    with pytest.raises(ValidationError, match="Invoice with ID .* not found"):
        service.get_invoice_allocations(
            invoice_id=invoice.id,
            organization_id=org2_id,
        )
