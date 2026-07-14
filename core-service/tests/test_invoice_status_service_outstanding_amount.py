"""
Unit Tests for InvoiceStatusService - Outstanding Amount Updates

These tests verify that the InvoiceStatusService.update_invoice_status() method
correctly updates the invoice.outstanding_amount field when payments are allocated
or cancelled.

**Validates: Requirements 2.12, 2.13**
"""

import uuid
from datetime import datetime, UTC
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.payment_entry import PaymentEntry
from app.models.payment_reference import PaymentReference
from app.models.customer import Customer
from app.models.base import (
    InvoiceType,
    InvoiceStatus,
    PaymentEntryType,
    PaymentMode,
    PaymentEntryStatus,
)
from app.services.invoice_status_service import InvoiceStatusService


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_customer(db_session, mock_current_user):
    """Create a sample customer for testing"""
    customer = Customer(
        id=uuid.uuid4(),
        organization_id=mock_current_user.organization_id,
        customer_name="Test Customer",
        customer_code="CUST-001",
        email="customer@example.com",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(customer)
    db_session.commit()
    return customer


# ============================================================================
# Outstanding Amount Update Tests
# ============================================================================

def test_outstanding_amount_equals_grand_total_with_no_allocations(
    db_session: Session,
    mock_current_user,
    sample_customer,
):
    """
    Test that outstanding_amount equals grand_total when there are no payment allocations.
    
    **Validates: Requirement 2.12**
    """
    org_id = mock_current_user.organization_id
    
    # Create a pending invoice with no payments
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-NO-ALLOC-{uuid.uuid4().hex[:8].upper()}",
        invoice_type=InvoiceType.SALES.value,
        party_id=sample_customer.id,
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status=InvoiceStatus.PENDING.value,
        grand_total=Decimal("1000.00"),
        outstanding_amount=Decimal("1000.00"),
        currency="USD",
        submitted_at=datetime.now(UTC),
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    # Update invoice status (no allocations)
    service = InvoiceStatusService(db_session)
    updated_invoice = service.update_invoice_status(
        invoice_id=invoice.id,
        organization_id=org_id,
    )
    
    # ASSERTION: Outstanding amount should equal grand_total
    assert updated_invoice.outstanding_amount == Decimal("1000.00"), (
        f"Invoice {invoice.invoice_no} with no allocations should have "
        f"outstanding_amount equal to grand_total (1000.00), "
        f"found {updated_invoice.outstanding_amount}"
    )
    
    # ASSERTION: Status should be "draft" (unpaid)
    assert updated_invoice.status == InvoiceStatus.DRAFT.value, (
        f"Invoice {invoice.invoice_no} with no allocations should have status 'draft', "
        f"found '{updated_invoice.status}'"
    )


def test_outstanding_amount_with_partial_allocation(
    db_session: Session,
    mock_current_user,
    sample_customer,
):
    """
    Test that outstanding_amount equals (grand_total - total_allocated) with partial payment.
    
    **Validates: Requirement 2.12**
    """
    org_id = mock_current_user.organization_id
    
    # Create a pending invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-PARTIAL-{uuid.uuid4().hex[:8].upper()}",
        invoice_type=InvoiceType.SALES.value,
        party_id=sample_customer.id,
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status=InvoiceStatus.PENDING.value,
        grand_total=Decimal("1000.00"),
        outstanding_amount=Decimal("1000.00"),
        currency="USD",
        submitted_at=datetime.now(UTC),
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    # Create a customer payment
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        payment_mode=PaymentMode.CASH,
        party_id=sample_customer.id,
        amount=Decimal("300.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        reference_no=f"PAY-{uuid.uuid4().hex[:8].upper()}",
        status=PaymentEntryStatus.CONFIRMED,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Allocate partial payment to invoice
    payment_reference = PaymentReference(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_id=payment.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("300.00"),
        created_by=mock_current_user.id,
    )
    db_session.add(payment_reference)
    db_session.commit()
    
    # Update invoice status
    service = InvoiceStatusService(db_session)
    updated_invoice = service.update_invoice_status(
        invoice_id=invoice.id,
        organization_id=org_id,
    )
    
    # ASSERTION: Outstanding amount should be grand_total - total_allocated
    expected_outstanding = Decimal("1000.00") - Decimal("300.00")
    assert updated_invoice.outstanding_amount == expected_outstanding, (
        f"Invoice {invoice.invoice_no} with partial allocation should have "
        f"outstanding_amount = {expected_outstanding}, "
        f"found {updated_invoice.outstanding_amount}"
    )
    
    # ASSERTION: Status should be "partial"
    assert updated_invoice.status == InvoiceStatus.PARTIAL.value, (
        f"Invoice {invoice.invoice_no} with partial allocation should have status 'partial', "
        f"found '{updated_invoice.status}'"
    )


def test_outstanding_amount_with_full_payment(
    db_session: Session,
    mock_current_user,
    sample_customer,
):
    """
    Test that outstanding_amount equals 0 when invoice is fully paid.
    
    **Validates: Requirement 2.12**
    """
    org_id = mock_current_user.organization_id
    
    # Create a pending invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-FULL-{uuid.uuid4().hex[:8].upper()}",
        invoice_type=InvoiceType.SALES.value,
        party_id=sample_customer.id,
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status=InvoiceStatus.PENDING.value,
        grand_total=Decimal("1000.00"),
        outstanding_amount=Decimal("1000.00"),
        currency="USD",
        submitted_at=datetime.now(UTC),
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    # Create a customer payment for full amount
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        payment_mode=PaymentMode.CASH,
        party_id=sample_customer.id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        reference_no=f"PAY-{uuid.uuid4().hex[:8].upper()}",
        status=PaymentEntryStatus.CONFIRMED,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Allocate full payment to invoice
    payment_reference = PaymentReference(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_id=payment.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("1000.00"),
        created_by=mock_current_user.id,
    )
    db_session.add(payment_reference)
    db_session.commit()
    
    # Update invoice status
    service = InvoiceStatusService(db_session)
    updated_invoice = service.update_invoice_status(
        invoice_id=invoice.id,
        organization_id=org_id,
    )
    
    # ASSERTION: Outstanding amount should be 0
    assert updated_invoice.outstanding_amount == Decimal("0.00"), (
        f"Invoice {invoice.invoice_no} with full payment should have "
        f"outstanding_amount = 0.00, "
        f"found {updated_invoice.outstanding_amount}"
    )
    
    # ASSERTION: Status should be "paid"
    assert updated_invoice.status == InvoiceStatus.PAID.value, (
        f"Invoice {invoice.invoice_no} with full payment should have status 'paid', "
        f"found '{updated_invoice.status}'"
    )


def test_outstanding_amount_with_overpayment(
    db_session: Session,
    mock_current_user,
    sample_customer,
):
    """
    Test that outstanding_amount is negative when invoice is overpaid.
    
    **Validates: Requirement 2.12**
    """
    org_id = mock_current_user.organization_id
    
    # Create a pending invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-OVER-{uuid.uuid4().hex[:8].upper()}",
        invoice_type=InvoiceType.SALES.value,
        party_id=sample_customer.id,
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status=InvoiceStatus.PENDING.value,
        grand_total=Decimal("1000.00"),
        outstanding_amount=Decimal("1000.00"),
        currency="USD",
        submitted_at=datetime.now(UTC),
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    # Create a customer payment for more than invoice amount
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        payment_mode=PaymentMode.CASH,
        party_id=sample_customer.id,
        amount=Decimal("1200.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        reference_no=f"PAY-{uuid.uuid4().hex[:8].upper()}",
        status=PaymentEntryStatus.CONFIRMED,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Allocate overpayment to invoice
    payment_reference = PaymentReference(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_id=payment.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("1200.00"),
        created_by=mock_current_user.id,
    )
    db_session.add(payment_reference)
    db_session.commit()
    
    # Update invoice status
    service = InvoiceStatusService(db_session)
    updated_invoice = service.update_invoice_status(
        invoice_id=invoice.id,
        organization_id=org_id,
    )
    
    # ASSERTION: Outstanding amount should be negative (overpaid)
    expected_outstanding = Decimal("1000.00") - Decimal("1200.00")
    assert updated_invoice.outstanding_amount == expected_outstanding, (
        f"Invoice {invoice.invoice_no} with overpayment should have "
        f"outstanding_amount = {expected_outstanding}, "
        f"found {updated_invoice.outstanding_amount}"
    )
    
    # ASSERTION: Outstanding amount should be less than 0
    assert updated_invoice.outstanding_amount < Decimal("0.00"), (
        f"Invoice {invoice.invoice_no} with overpayment should have "
        f"outstanding_amount < 0, found {updated_invoice.outstanding_amount}"
    )
    
    # ASSERTION: Status should be "paid" (overpaid is still considered paid)
    assert updated_invoice.status == InvoiceStatus.PAID.value, (
        f"Invoice {invoice.invoice_no} with overpayment should have status 'paid', "
        f"found '{updated_invoice.status}'"
    )


def test_outstanding_amount_after_payment_cancellation(
    db_session: Session,
    mock_current_user,
    sample_customer,
):
    """
    Test that outstanding_amount increases when a payment allocation is cancelled.
    
    **Validates: Requirement 2.13**
    """
    org_id = mock_current_user.organization_id
    
    # Create a pending invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-CANCEL-{uuid.uuid4().hex[:8].upper()}",
        invoice_type=InvoiceType.SALES.value,
        party_id=sample_customer.id,
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status=InvoiceStatus.PENDING.value,
        grand_total=Decimal("1000.00"),
        outstanding_amount=Decimal("1000.00"),
        currency="USD",
        submitted_at=datetime.now(UTC),
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    # Create a customer payment
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        payment_mode=PaymentMode.CASH,
        party_id=sample_customer.id,
        amount=Decimal("300.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        reference_no=f"PAY-{uuid.uuid4().hex[:8].upper()}",
        status=PaymentEntryStatus.CONFIRMED,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Allocate payment to invoice
    payment_reference = PaymentReference(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_id=payment.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("300.00"),
        created_by=mock_current_user.id,
    )
    db_session.add(payment_reference)
    db_session.commit()
    
    # Update invoice status after allocation
    service = InvoiceStatusService(db_session)
    updated_invoice = service.update_invoice_status(
        invoice_id=invoice.id,
        organization_id=org_id,
    )
    
    # Verify outstanding amount after allocation
    assert updated_invoice.outstanding_amount == Decimal("700.00"), (
        f"Invoice {invoice.invoice_no} should have outstanding_amount = 700.00 after allocation"
    )
    
    # Cancel the payment allocation
    db_session.delete(payment_reference)
    db_session.commit()
    
    # Update invoice status after cancellation
    updated_invoice = service.update_invoice_status(
        invoice_id=invoice.id,
        organization_id=org_id,
    )
    
    # ASSERTION: Outstanding amount should increase back to grand_total
    assert updated_invoice.outstanding_amount == Decimal("1000.00"), (
        f"Invoice {invoice.invoice_no} should have outstanding_amount = 1000.00 "
        f"after payment cancellation, found {updated_invoice.outstanding_amount}"
    )
    
    # ASSERTION: Status should be "draft" (unpaid)
    assert updated_invoice.status == InvoiceStatus.DRAFT.value, (
        f"Invoice {invoice.invoice_no} should have status 'draft' after payment cancellation, "
        f"found '{updated_invoice.status}'"
    )
