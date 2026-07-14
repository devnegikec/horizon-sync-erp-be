"""
Bug 3 Exploration Tests: Outstanding Amount Not Updated

These tests are EXPECTED TO FAIL on unfixed code to confirm the bug exists.
They test that allocating payments to invoices should update invoice.outstanding_amount
to reflect the remaining balance (grand_total - total_allocated).

**CRITICAL**: These tests encode the expected behavior and will validate the fix
when they pass after implementation. For now, they should fail to demonstrate
the bug exists.

**Validates: Requirements 2.12, 2.13**
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
from app.models.base import InvoiceType, PaymentEntryType, PaymentMode, PaymentEntryStatus, PaymentSource
from app.services.allocation_service import AllocationService


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def create_test_invoice(db_session, mock_current_user):
    """Helper fixture to create a test invoice"""
    def _create_invoice(grand_total: Decimal, invoice_no: str = None):
        org_id = mock_current_user.organization_id
        
        if invoice_no is None:
            invoice_no = f"INV-TEST-{uuid.uuid4().hex[:8].upper()}"
        
        invoice = Invoice(
            id=uuid.uuid4(),
            organization_id=org_id,
            invoice_no=invoice_no,
            invoice_type=InvoiceType.SALES,
            party_id=uuid.uuid4(),
            party_type="Customer",
            posting_date=datetime.now(UTC),
            status="submitted",  # Already confirmed
            submitted_at=datetime.now(UTC),
            grand_total=grand_total,
            outstanding_amount=grand_total,  # Initially equals grand_total
            currency="USD",
            created_by=mock_current_user.id,
            updated_by=mock_current_user.id,
        )
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)
        return invoice
    
    return _create_invoice


@pytest.fixture
def create_test_payment(db_session, mock_current_user):
    """Helper fixture to create a test payment"""
    def _create_payment(amount: Decimal, party_id: uuid.UUID, reference_no: str = None):
        org_id = mock_current_user.organization_id
        
        if reference_no is None:
            reference_no = f"PAY-TEST-{uuid.uuid4().hex[:8].upper()}"
        
        payment = PaymentEntry(
            id=uuid.uuid4(),
            organization_id=org_id,
            payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
            party_id=party_id,
            amount=amount,
            currency_code="USD",
            payment_date=datetime.now(UTC),
            payment_mode=PaymentMode.CASH,
            reference_no=reference_no,
            status=PaymentEntryStatus.DRAFT,  # Must be draft to allocate
            source=PaymentSource.MANUAL,
            created_by=mock_current_user.id,
            updated_by=mock_current_user.id,
        )
        db_session.add(payment)
        db_session.commit()
        db_session.refresh(payment)
        return payment
    
    return _create_payment


# ============================================================================
# Bug 3 Exploration Tests - Payment Allocation
# ============================================================================

def test_payment_allocation_updates_outstanding_amount(
    db_session: Session,
    mock_current_user,
    create_test_invoice,
    create_test_payment
):
    """
    Test that allocating a payment to an invoice updates invoice.outstanding_amount
    to (grand_total - total_allocated).
    
    **EXPECTED OUTCOME**: This test FAILS on unfixed code (outstanding_amount not updated)
    **Validates: Requirement 2.12**
    """
    org_id = mock_current_user.organization_id
    
    # Create invoice with grand_total $1000
    invoice = create_test_invoice(Decimal("1000.00"), "INV-001")
    
    # Verify initial outstanding_amount equals grand_total
    assert invoice.outstanding_amount == Decimal("1000.00"), (
        "Initial outstanding_amount should equal grand_total"
    )
    
    # Create payment for $300
    payment = create_test_payment(Decimal("300.00"), invoice.party_id, "PAY-001")
    
    # Allocate payment to invoice
    allocation_service = AllocationService(db_session)
    allocation = allocation_service.create_allocation(
        payment_id=payment.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("300.00"),
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Refresh invoice to get updated values
    db_session.refresh(invoice)
    
    # ASSERTION: outstanding_amount should be $700 (will FAIL on unfixed code)
    expected_outstanding = Decimal("700.00")
    assert invoice.outstanding_amount == expected_outstanding, (
        f"Invoice {invoice.invoice_no} with grand_total $1000, payment allocated $300, "
        f"but outstanding_amount is {invoice.outstanding_amount} instead of {expected_outstanding}. "
        f"Expected outstanding_amount to be updated to (grand_total - total_allocated)."
    )


def test_payment_cancellation_increases_outstanding_amount(
    db_session: Session,
    mock_current_user,
    create_test_invoice,
    create_test_payment
):
    """
    Test that cancelling a payment allocation increases invoice.outstanding_amount
    back to reflect the removed allocation.
    
    **EXPECTED OUTCOME**: This test FAILS on unfixed code (outstanding_amount not updated)
    **Validates: Requirement 2.13**
    """
    org_id = mock_current_user.organization_id
    
    # Create invoice with grand_total $1000
    invoice = create_test_invoice(Decimal("1000.00"), "INV-002")
    
    # Create and allocate payment for $300
    payment = create_test_payment(Decimal("300.00"), invoice.party_id, "PAY-002")
    
    allocation_service = AllocationService(db_session)
    allocation = allocation_service.create_allocation(
        payment_id=payment.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("300.00"),
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Refresh invoice
    db_session.refresh(invoice)
    
    # Verify outstanding_amount is $700 after allocation
    # (This assertion may also fail if Bug 3 exists, but we continue to test cancellation)
    initial_outstanding = invoice.outstanding_amount
    
    # Cancel the payment allocation
    allocation_service.remove_allocation(
        allocation_id=allocation.id,
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Refresh invoice to get updated values
    db_session.refresh(invoice)
    
    # ASSERTION: outstanding_amount should increase back to $1000 (will FAIL on unfixed code)
    expected_outstanding = Decimal("1000.00")
    assert invoice.outstanding_amount == expected_outstanding, (
        f"Invoice {invoice.invoice_no} had outstanding_amount {initial_outstanding} after $300 allocation, "
        f"but after cancelling the allocation, outstanding_amount is {invoice.outstanding_amount} "
        f"instead of {expected_outstanding}. Expected outstanding_amount to increase back to grand_total "
        f"when payment allocation is cancelled."
    )


def test_multiple_partial_payments_update_outstanding_amount(
    db_session: Session,
    mock_current_user,
    create_test_invoice,
    create_test_payment
):
    """
    Test that multiple partial payments correctly update outstanding_amount
    to reflect the sum of all allocations.
    
    **EXPECTED OUTCOME**: This test FAILS on unfixed code (outstanding_amount not updated)
    **Validates: Requirement 2.12**
    """
    org_id = mock_current_user.organization_id
    
    # Create invoice with grand_total $1000
    invoice = create_test_invoice(Decimal("1000.00"), "INV-003")
    
    allocation_service = AllocationService(db_session)
    
    # First payment: $200
    payment1 = create_test_payment(Decimal("200.00"), invoice.party_id, "PAY-003-1")
    allocation_service.create_allocation(
        payment_id=payment1.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("200.00"),
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    db_session.refresh(invoice)
    
    # ASSERTION 1: outstanding_amount should be $800
    assert invoice.outstanding_amount == Decimal("800.00"), (
        f"After first payment of $200, outstanding_amount should be $800, "
        f"but found {invoice.outstanding_amount}"
    )
    
    # Second payment: $300
    payment2 = create_test_payment(Decimal("300.00"), invoice.party_id, "PAY-003-2")
    allocation_service.create_allocation(
        payment_id=payment2.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("300.00"),
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    db_session.refresh(invoice)
    
    # ASSERTION 2: outstanding_amount should be $500
    assert invoice.outstanding_amount == Decimal("500.00"), (
        f"After second payment of $300 (total $500), outstanding_amount should be $500, "
        f"but found {invoice.outstanding_amount}"
    )
    
    # Third payment: $400
    payment3 = create_test_payment(Decimal("400.00"), invoice.party_id, "PAY-003-3")
    allocation_service.create_allocation(
        payment_id=payment3.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("400.00"),
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    db_session.refresh(invoice)
    
    # ASSERTION 3: outstanding_amount should be $100
    expected_outstanding = Decimal("100.00")
    assert invoice.outstanding_amount == expected_outstanding, (
        f"Invoice {invoice.invoice_no} with grand_total $1000, "
        f"three payments allocated ($200 + $300 + $400 = $900), "
        f"but outstanding_amount is {invoice.outstanding_amount} instead of {expected_outstanding}. "
        f"Expected outstanding_amount to reflect sum of all allocations."
    )


def test_full_payment_sets_outstanding_amount_to_zero(
    db_session: Session,
    mock_current_user,
    create_test_invoice,
    create_test_payment
):
    """
    Test that fully paying an invoice sets outstanding_amount to zero
    and updates status to "paid".
    
    **EXPECTED OUTCOME**: This test may PASS or FAIL depending on implementation
    **Validates: Requirement 2.12**
    """
    org_id = mock_current_user.organization_id
    
    # Create invoice with grand_total $1000
    invoice = create_test_invoice(Decimal("1000.00"), "INV-004")
    
    # Create payment for full amount $1000
    payment = create_test_payment(Decimal("1000.00"), invoice.party_id, "PAY-004")
    
    allocation_service = AllocationService(db_session)
    allocation_service.create_allocation(
        payment_id=payment.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("1000.00"),
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Refresh invoice
    db_session.refresh(invoice)
    
    # ASSERTION 1: outstanding_amount should be $0
    assert invoice.outstanding_amount == Decimal("0.00"), (
        f"Invoice {invoice.invoice_no} fully paid with $1000, "
        f"but outstanding_amount is {invoice.outstanding_amount} instead of $0. "
        f"Expected outstanding_amount to be zero when invoice is fully paid."
    )
    
    # ASSERTION 2: status should be "paid"
    assert invoice.status == "paid", (
        f"Invoice {invoice.invoice_no} fully paid, "
        f"but status is '{invoice.status}' instead of 'paid'. "
        f"Expected status to be updated to 'paid' when outstanding_amount reaches zero."
    )


# ============================================================================
# Property-Based Test: Outstanding Amount Updates
# ============================================================================

@given(
    grand_total=st.decimals(
        min_value=Decimal("100.00"),
        max_value=Decimal("9999.99"),
        places=2
    ),
    allocated_amount=st.decimals(
        min_value=Decimal("10.00"),
        max_value=Decimal("99.99"),
        places=2
    )
)
@settings(
    max_examples=5,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None
)
def test_property_outstanding_amount_equals_grand_total_minus_allocated(
    db_session: Session,
    mock_current_user,
    create_test_invoice,
    create_test_payment,
    grand_total: Decimal,
    allocated_amount: Decimal
):
    """
    Property-Based Test: For any invoice with grand_total and any payment allocation,
    the outstanding_amount should equal (grand_total - total_allocated).
    
    **EXPECTED OUTCOME**: This test FAILS on unfixed code (outstanding_amount not updated)
    **Validates: Requirements 2.12, 2.13**
    """
    org_id = mock_current_user.organization_id
    
    # Ensure allocated_amount doesn't exceed grand_total
    if allocated_amount > grand_total:
        allocated_amount = grand_total
    
    # Create invoice
    invoice = create_test_invoice(grand_total, f"INV-PBT-{uuid.uuid4().hex[:8].upper()}")
    
    # Create payment
    payment = create_test_payment(
        allocated_amount,
        invoice.party_id,
        f"PAY-PBT-{uuid.uuid4().hex[:8].upper()}"
    )
    
    # Allocate payment to invoice
    allocation_service = AllocationService(db_session)
    allocation = allocation_service.create_allocation(
        payment_id=payment.id,
        invoice_id=invoice.id,
        allocated_amount=allocated_amount,
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Refresh invoice
    db_session.refresh(invoice)
    
    # Property: outstanding_amount = grand_total - allocated_amount
    expected_outstanding = grand_total - allocated_amount
    assert invoice.outstanding_amount == expected_outstanding, (
        f"Invoice {invoice.invoice_no} (grand_total={grand_total}, "
        f"allocated={allocated_amount}) has outstanding_amount={invoice.outstanding_amount}, "
        f"expected {expected_outstanding}. Property violated: "
        f"outstanding_amount should equal (grand_total - total_allocated)"
    )
    
    # Cleanup for next iteration
    allocation_service.remove_allocation(
        allocation_id=allocation.id,
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    db_session.delete(payment)
    db_session.delete(invoice)
    db_session.commit()


@given(
    grand_total=st.decimals(
        min_value=Decimal("100.00"),
        max_value=Decimal("9999.99"),
        places=2
    ),
    num_payments=st.integers(min_value=2, max_value=5)
)
@settings(
    max_examples=5,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None
)
def test_property_multiple_allocations_sum_correctly(
    db_session: Session,
    mock_current_user,
    create_test_invoice,
    create_test_payment,
    grand_total: Decimal,
    num_payments: int
):
    """
    Property-Based Test: For any invoice with multiple payment allocations,
    the outstanding_amount should equal (grand_total - sum of all allocations).
    
    **EXPECTED OUTCOME**: This test FAILS on unfixed code (outstanding_amount not updated)
    **Validates: Requirement 2.12**
    """
    org_id = mock_current_user.organization_id
    
    # Create invoice
    invoice = create_test_invoice(grand_total, f"INV-MULTI-{uuid.uuid4().hex[:8].upper()}")
    
    # Calculate payment amounts (divide grand_total by num_payments, with some variation)
    base_amount = (grand_total / Decimal(num_payments)).quantize(Decimal("0.01"))
    payment_amounts = [base_amount] * num_payments
    
    # Adjust last payment to ensure total doesn't exceed grand_total
    total_allocated = sum(payment_amounts)
    if total_allocated > grand_total:
        payment_amounts[-1] = payment_amounts[-1] - (total_allocated - grand_total)
    
    # Create and allocate multiple payments
    allocation_service = AllocationService(db_session)
    allocations = []
    
    for i, amount in enumerate(payment_amounts):
        if amount <= 0:
            continue
            
        payment = create_test_payment(
            amount,
            invoice.party_id,
            f"PAY-MULTI-{i}-{uuid.uuid4().hex[:8].upper()}"
        )
        
        allocation = allocation_service.create_allocation(
            payment_id=payment.id,
            invoice_id=invoice.id,
            allocated_amount=amount,
            organization_id=org_id,
            user_id=mock_current_user.id,
        )
        allocations.append((allocation, payment))
    
    # Refresh invoice
    db_session.refresh(invoice)
    
    # Property: outstanding_amount = grand_total - sum(all allocations)
    total_allocated = sum(amount for amount in payment_amounts if amount > 0)
    expected_outstanding = grand_total - total_allocated
    
    assert invoice.outstanding_amount == expected_outstanding, (
        f"Invoice {invoice.invoice_no} (grand_total={grand_total}) with "
        f"{len(allocations)} payments (total={total_allocated}) has "
        f"outstanding_amount={invoice.outstanding_amount}, expected {expected_outstanding}. "
        f"Property violated: outstanding_amount should equal (grand_total - sum of all allocations)"
    )
    
    # Cleanup for next iteration
    for allocation, payment in allocations:
        allocation_service.remove_allocation(
            allocation_id=allocation.id,
            organization_id=org_id,
            user_id=mock_current_user.id,
        )
        db_session.delete(payment)
    db_session.delete(invoice)
    db_session.commit()
