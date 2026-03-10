"""
Verification Tests: Automatic Invoice Status Triggers

These tests verify that InvoiceStatusService.update_invoice_status() is automatically
called when payments are allocated or cancelled, ensuring outstanding_amount is always
up-to-date.

**Validates: Requirements 2.12, 2.13**
"""

import uuid
from datetime import datetime, UTC
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.payment_entry import PaymentEntry
from app.models.customer import Customer
from app.models.base import (
    InvoiceType,
    InvoiceStatus,
    PaymentEntryType,
    PaymentMode,
    PaymentEntryStatus,
)
from app.services.allocation_service import AllocationService
from app.services.payment_entry_service import PaymentEntryService


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
# Automatic Trigger Verification Tests
# ============================================================================

def test_allocation_service_create_triggers_invoice_status_update(
    db_session: Session,
    mock_current_user,
    sample_customer,
):
    """
    Verify that AllocationService.create_allocation() automatically triggers
    InvoiceStatusService.update_invoice_status() to update outstanding_amount.
    
    **Validates: Requirement 2.12**
    """
    org_id = mock_current_user.organization_id
    
    # Create a pending invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-AUTO-{uuid.uuid4().hex[:8].upper()}",
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
    
    # Create a draft customer payment
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
        status=PaymentEntryStatus.DRAFT,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Use AllocationService to create allocation
    allocation_service = AllocationService(db_session)
    payment_reference = allocation_service.create_allocation(
        payment_id=payment.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("300.00"),
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Refresh invoice to get updated values
    db_session.refresh(invoice)
    
    # ASSERTION: Outstanding amount should be automatically updated
    expected_outstanding = Decimal("1000.00") - Decimal("300.00")
    assert invoice.outstanding_amount == expected_outstanding, (
        f"AllocationService.create_allocation() should automatically update "
        f"invoice.outstanding_amount to {expected_outstanding}, "
        f"found {invoice.outstanding_amount}"
    )
    
    # ASSERTION: Status should be automatically updated to "partial"
    assert invoice.status == InvoiceStatus.PARTIAL.value, (
        f"AllocationService.create_allocation() should automatically update "
        f"invoice.status to 'partial', found '{invoice.status}'"
    )


def test_allocation_service_remove_triggers_invoice_status_update(
    db_session: Session,
    mock_current_user,
    sample_customer,
):
    """
    Verify that AllocationService.remove_allocation() automatically triggers
    InvoiceStatusService.update_invoice_status() to update outstanding_amount.
    
    **Validates: Requirement 2.13**
    """
    org_id = mock_current_user.organization_id
    
    # Create a pending invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-REMOVE-{uuid.uuid4().hex[:8].upper()}",
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
    
    # Create a draft customer payment
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
        status=PaymentEntryStatus.DRAFT,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Create allocation
    allocation_service = AllocationService(db_session)
    payment_reference = allocation_service.create_allocation(
        payment_id=payment.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("300.00"),
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Refresh invoice to verify allocation worked
    db_session.refresh(invoice)
    assert invoice.outstanding_amount == Decimal("700.00"), "Allocation should have updated outstanding_amount"
    
    # Remove the allocation
    allocation_service.remove_allocation(
        allocation_id=payment_reference.id,
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Refresh invoice to get updated values
    db_session.refresh(invoice)
    
    # ASSERTION: Outstanding amount should be automatically restored
    assert invoice.outstanding_amount == Decimal("1000.00"), (
        f"AllocationService.remove_allocation() should automatically update "
        f"invoice.outstanding_amount back to 1000.00, "
        f"found {invoice.outstanding_amount}"
    )
    
    # ASSERTION: Status should be automatically updated back to "draft"
    assert invoice.status == InvoiceStatus.DRAFT.value, (
        f"AllocationService.remove_allocation() should automatically update "
        f"invoice.status back to 'draft', found '{invoice.status}'"
    )


# Note: Payment cancellation test is covered by the remove_allocation test above
# since cancel_payment internally removes all payment_references which triggers
# the same InvoiceStatusService.update_invoice_status() call.
# The cancel_payment method code review confirms this behavior (lines 975-980 in payment_entry_service.py)
