"""
Phase 2 Preservation Tests: Invoice Status Transitions

These tests verify that invoice status transitions remain unchanged after the fix.
Invoice status should automatically update from "pending" to "paid" or "partial"
based on payment allocations via InvoiceStatusService. Updating already-confirmed
invoices should not create duplicate journal entries.

**CRITICAL**: These tests encode the expected preservation behavior. They should
pass on both unfixed and fixed code to ensure no regression.

**Validates: Requirements 3.9, 3.10**
"""

import uuid
from datetime import datetime, UTC
from decimal import Decimal

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.payment_entry import PaymentEntry
from app.models.payment_reference import PaymentReference
from app.models.journal_entry import JournalEntry
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.base import (
    InvoiceType,
    InvoiceStatus,
    PaymentEntryType,
    PaymentMode,
    PaymentEntryStatus,
)
from app.services.invoice_status_service import InvoiceStatusService
from app.services.invoice_service import InvoiceService


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


@pytest.fixture
def sample_supplier(db_session, mock_current_user):
    """Create a sample supplier for testing"""
    supplier = Supplier(
        id=uuid.uuid4(),
        organization_id=mock_current_user.organization_id,
        supplier_name="Test Supplier",
        supplier_code="SUPP-001",
        email="supplier@example.com",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(supplier)
    db_session.commit()
    return supplier


# ============================================================================
# Invoice Status Transition Tests
# ============================================================================

def test_invoice_status_changes_to_paid_when_fully_paid(
    db_session: Session,
    mock_current_user,
    sample_customer,
):
    """
    Test that invoice status changes from "pending" to "paid" when fully paid
    via InvoiceStatusService.
    
    **EXPECTED OUTCOME**: This test PASSES on unfixed code (preservation test)
    **Validates: Requirement 3.9**
    """
    org_id = mock_current_user.organization_id
    
    # Create a pending sales invoice (representing a confirmed invoice)
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-PENDING-{uuid.uuid4().hex[:8].upper()}",
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
    
    # Allocate payment to invoice (full payment)
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
    
    # Update invoice status using InvoiceStatusService
    service = InvoiceStatusService(db_session)
    updated_invoice = service.update_invoice_status(
        invoice_id=invoice.id,
        organization_id=org_id,
    )
    
    # ASSERTION: Invoice status should change to "paid"
    assert updated_invoice.status == InvoiceStatus.PAID.value, (
        f"Invoice {invoice.invoice_no} should have status 'paid' after full payment, "
        f"found '{updated_invoice.status}'"
    )
    
    # ASSERTION: Outstanding amount should be 0
    assert updated_invoice.outstanding_amount == Decimal("0.00"), (
        f"Invoice {invoice.invoice_no} should have outstanding_amount 0 after full payment, "
        f"found {updated_invoice.outstanding_amount}"
    )


def test_invoice_status_changes_to_partial_when_partially_paid(
    db_session: Session,
    mock_current_user,
    sample_customer,
):
    """
    Test that invoice status changes from "pending" to "partial" when partially paid
    via InvoiceStatusService.
    
    **EXPECTED OUTCOME**: This test PASSES on unfixed code (preservation test)
    **Validates: Requirement 3.9**
    """
    org_id = mock_current_user.organization_id
    
    # Create a pending sales invoice (representing a confirmed invoice)
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-PENDING-{uuid.uuid4().hex[:8].upper()}",
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
    
    # Allocate payment to invoice (partial payment)
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
    
    # Update invoice status using InvoiceStatusService
    service = InvoiceStatusService(db_session)
    updated_invoice = service.update_invoice_status(
        invoice_id=invoice.id,
        organization_id=org_id,
    )
    
    # ASSERTION: Invoice status should change to "partial"
    assert updated_invoice.status == InvoiceStatus.PARTIAL.value, (
        f"Invoice {invoice.invoice_no} should have status 'partial' after partial payment, "
        f"found '{updated_invoice.status}'"
    )
    
    # ASSERTION: Outstanding amount should be 700
    assert updated_invoice.outstanding_amount == Decimal("700.00"), (
        f"Invoice {invoice.invoice_no} should have outstanding_amount 700 after partial payment, "
        f"found {updated_invoice.outstanding_amount}"
    )


def test_updating_confirmed_invoice_does_not_create_duplicate_journal_entries(
    db_session: Session,
    mock_current_user,
    sample_customer,
):
    """
    Test that updating an already-confirmed invoice (changing remarks) does not
    create duplicate journal entries.
    
    **EXPECTED OUTCOME**: This test PASSES on unfixed code (preservation test)
    **Validates: Requirement 3.10**
    """
    org_id = mock_current_user.organization_id
    
    # Create a pending sales invoice (representing a confirmed invoice)
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-PENDING-{uuid.uuid4().hex[:8].upper()}",
        invoice_type=InvoiceType.SALES.value,
        party_id=sample_customer.id,
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status=InvoiceStatus.PENDING.value,
        grand_total=Decimal("1000.00"),
        outstanding_amount=Decimal("1000.00"),
        currency="USD",
        submitted_at=datetime.now(UTC),
        remarks="Original remarks",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    # Count journal entries before update
    journal_entries_before = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "Invoice",
        JournalEntry.reference_id == invoice.id,
        JournalEntry.organization_id == org_id
    ).all()
    
    count_before = len(journal_entries_before)
    
    # Update the confirmed invoice (change remarks only, not re-confirming)
    service = InvoiceService(db_session)
    updated_invoice = service.update(
        invoice_id=invoice.id,
        data={
            "remarks": "Updated remarks - should not create duplicate journal entry",
        },
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Count journal entries after update
    journal_entries_after = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "Invoice",
        JournalEntry.reference_id == invoice.id,
        JournalEntry.organization_id == org_id
    ).all()
    
    count_after = len(journal_entries_after)
    
    # ASSERTION: No new journal entries should be created
    assert count_after == count_before, (
        f"Updating confirmed invoice {invoice.invoice_no} should not create duplicate "
        f"journal entries. Before: {count_before}, After: {count_after}"
    )
    
    # Verify invoice was updated
    assert updated_invoice["remarks"] == "Updated remarks - should not create duplicate journal entry", (
        "Invoice remarks should be updated"
    )
    assert updated_invoice["status"] == InvoiceStatus.PENDING.value, (
        "Invoice status should remain 'pending'"
    )


# ============================================================================
# Property-Based Test: Invoice Status Transitions
# ============================================================================

@given(
    grand_total=st.decimals(
        min_value=Decimal("100.00"),
        max_value=Decimal("9999.99"),
        places=2
    ),
    payment_ratio=st.sampled_from([
        Decimal("0.3"),   # 30% - partial payment
        Decimal("0.5"),   # 50% - partial payment
        Decimal("0.7"),   # 70% - partial payment
        Decimal("1.0"),   # 100% - full payment
    ])
)
@settings(
    max_examples=5,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None
)
def test_property_invoice_status_transitions_automatic(
    db_session: Session,
    mock_current_user,
    sample_customer,
    grand_total: Decimal,
    payment_ratio: Decimal,
):
    """
    Property-Based Test: For all invoice status transitions due to payment
    allocations, status updates automatically without duplicate journal entries.
    
    **EXPECTED OUTCOME**: This test PASSES on unfixed code (preservation test)
    **Validates: Requirements 3.9, 3.10**
    """
    org_id = mock_current_user.organization_id
    
    # Create a pending sales invoice (representing a confirmed invoice)
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-PBT-{uuid.uuid4().hex[:8].upper()}",
        invoice_type=InvoiceType.SALES.value,
        party_id=sample_customer.id,
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status=InvoiceStatus.PENDING.value,
        grand_total=grand_total,
        outstanding_amount=grand_total,
        currency="USD",
        submitted_at=datetime.now(UTC),
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    # Calculate payment amount based on ratio
    payment_amount = (grand_total * payment_ratio).quantize(Decimal("0.01"))
    
    # Create a customer payment
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        payment_mode=PaymentMode.CASH,
        party_id=sample_customer.id,
        amount=payment_amount,
        currency_code="USD",
        payment_date=datetime.now(UTC),
        reference_no=f"PAY-PBT-{uuid.uuid4().hex[:8].upper()}",
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
        allocated_amount=payment_amount,
        created_by=mock_current_user.id,
    )
    db_session.add(payment_reference)
    db_session.commit()
    
    # Count journal entries before status update
    journal_entries_before = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "Invoice",
        JournalEntry.reference_id == invoice.id,
        JournalEntry.organization_id == org_id
    ).all()
    count_before = len(journal_entries_before)
    
    # Update invoice status using InvoiceStatusService
    service = InvoiceStatusService(db_session)
    updated_invoice = service.update_invoice_status(
        invoice_id=invoice.id,
        organization_id=org_id,
    )
    
    # Count journal entries after status update
    journal_entries_after = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "Invoice",
        JournalEntry.reference_id == invoice.id,
        JournalEntry.organization_id == org_id
    ).all()
    count_after = len(journal_entries_after)
    
    # Property 1: Status updates automatically based on payment allocation
    expected_status = InvoiceStatus.PAID.value if payment_ratio == Decimal("1.0") else InvoiceStatus.PARTIAL.value
    assert updated_invoice.status == expected_status, (
        f"Invoice {invoice.invoice_no} (grand_total={grand_total}, "
        f"payment_ratio={payment_ratio}) should have status '{expected_status}', "
        f"found '{updated_invoice.status}'"
    )
    
    # Property 2: Outstanding amount is calculated correctly
    expected_outstanding = grand_total - payment_amount
    assert updated_invoice.outstanding_amount == expected_outstanding, (
        f"Invoice {invoice.invoice_no} should have outstanding_amount "
        f"{expected_outstanding}, found {updated_invoice.outstanding_amount}"
    )
    
    # Property 3: No duplicate journal entries created during status update
    assert count_after == count_before, (
        f"Invoice status update should not create duplicate journal entries. "
        f"Before: {count_before}, After: {count_after}"
    )
    
    # Cleanup
    db_session.delete(payment_reference)
    db_session.delete(payment)
    db_session.delete(invoice)
    db_session.commit()
