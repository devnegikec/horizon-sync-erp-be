"""
Phase 2 Preservation Tests: Draft Invoice Operations

These tests verify that draft invoice CRUD operations remain unchanged after the fix.
Draft invoices should NOT create journal entries. These tests should PASS on UNFIXED
code to confirm baseline behavior that must be preserved.

**CRITICAL**: These tests encode the expected preservation behavior. They should
pass on both unfixed and fixed code to ensure no regression.

**Validates: Requirements 3.6, 3.7, 3.8**
"""

import uuid
from datetime import datetime, UTC
from decimal import Decimal

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceItem
from app.models.journal_entry import JournalEntry
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.base import InvoiceType, InvoiceStatus
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
# Draft Invoice Creation Tests
# ============================================================================

def test_creating_draft_invoice_does_not_create_journal_entry(
    db_session: Session,
    mock_current_user,
    sample_customer,
):
    """
    Test that creating a draft invoice does NOT create journal entries.
    
    **EXPECTED OUTCOME**: This test PASSES on unfixed code (preservation test)
    **Validates: Requirement 3.6**
    """
    org_id = mock_current_user.organization_id
    
    # Create a draft sales invoice directly (without items to avoid complexity)
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-DRAFT-{uuid.uuid4().hex[:8].upper()}",
        invoice_type=InvoiceType.SALES.value,
        party_id=sample_customer.id,
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status=InvoiceStatus.DRAFT.value,
        grand_total=Decimal("1000.00"),
        currency="USD",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    invoice_id = invoice.id
    
    # Query for journal entries related to this invoice
    journal_entries = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "Invoice",
        JournalEntry.reference_id == invoice_id,
        JournalEntry.organization_id == org_id
    ).all()
    
    # ASSERTION: No journal entry should exist for draft invoice
    assert len(journal_entries) == 0, (
        f"Draft invoice {invoice.invoice_no} should NOT create journal entry. "
        f"Found {len(journal_entries)} journal entries."
    )
    
    # Verify invoice was created with draft status
    assert invoice.status == InvoiceStatus.DRAFT.value, (
        f"Invoice status should be 'draft', found '{invoice.status}'"
    )


# ============================================================================
# Draft Invoice Update Tests
# ============================================================================

def test_updating_draft_invoice_does_not_create_journal_entry(
    db_session: Session,
    mock_current_user,
    sample_customer,
):
    """
    Test that updating a draft invoice does NOT create journal entries.
    
    **EXPECTED OUTCOME**: This test PASSES on unfixed code (preservation test)
    **Validates: Requirement 3.7**
    """
    org_id = mock_current_user.organization_id
    
    # Create a draft sales invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-DRAFT-{uuid.uuid4().hex[:8].upper()}",
        invoice_type=InvoiceType.SALES.value,
        party_id=sample_customer.id,
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status=InvoiceStatus.DRAFT.value,
        grand_total=Decimal("1000.00"),
        currency="USD",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    # Update the draft invoice (change grand_total and remarks)
    service = InvoiceService(db_session)
    updated_invoice = service.update(
        invoice_id=invoice.id,
        data={
            "grand_total": Decimal("1500.00"),
            "remarks": "Updated draft invoice",
        },
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Query for journal entries related to this invoice
    journal_entries = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "Invoice",
        JournalEntry.reference_id == invoice.id,
        JournalEntry.organization_id == org_id
    ).all()
    
    # ASSERTION: No journal entry should exist for draft invoice update
    assert len(journal_entries) == 0, (
        f"Updating draft invoice {invoice.invoice_no} should NOT create journal entry. "
        f"Found {len(journal_entries)} journal entries."
    )
    
    # Verify invoice was updated
    assert str(updated_invoice["grand_total"]) == "1500.00", (
        "Invoice grand_total should be updated"
    )
    assert updated_invoice["status"] == InvoiceStatus.DRAFT.value, (
        "Invoice status should remain 'draft'"
    )


# ============================================================================
# Draft Invoice Deletion Tests
# ============================================================================

def test_deleting_draft_invoice_does_not_affect_journal_entries(
    db_session: Session,
    mock_current_user,
    sample_customer,
):
    """
    Test that deleting a draft invoice does NOT affect journal entries.
    Since draft invoices don't have journal entries, this test verifies
    that deletion completes successfully without any journal entry operations.
    
    **EXPECTED OUTCOME**: This test PASSES on unfixed code (preservation test)
    **Validates: Requirement 3.8**
    """
    org_id = mock_current_user.organization_id
    
    # Create a draft sales invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-DRAFT-{uuid.uuid4().hex[:8].upper()}",
        invoice_type=InvoiceType.SALES.value,
        party_id=sample_customer.id,
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status=InvoiceStatus.DRAFT.value,
        grand_total=Decimal("1000.00"),
        currency="USD",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    invoice_id = invoice.id
    invoice_no = invoice.invoice_no
    
    # Verify no journal entries exist before deletion
    journal_entries_before = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "Invoice",
        JournalEntry.reference_id == invoice_id,
        JournalEntry.organization_id == org_id
    ).all()
    
    assert len(journal_entries_before) == 0, (
        "Draft invoice should not have journal entries before deletion"
    )
    
    # Delete the draft invoice
    service = InvoiceService(db_session)
    service.delete(
        invoice_id=invoice_id,
        organization_id=org_id,
    )
    
    # Verify invoice was deleted
    deleted_invoice = db_session.query(Invoice).filter(Invoice.id == invoice_id).first()
    assert deleted_invoice is None, (
        f"Invoice {invoice_no} should be deleted"
    )
    
    # Verify no journal entries were created or affected during deletion
    journal_entries_after = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "Invoice",
        JournalEntry.reference_id == invoice_id,
        JournalEntry.organization_id == org_id
    ).all()
    
    assert len(journal_entries_after) == 0, (
        f"Deleting draft invoice {invoice_no} should not create or affect journal entries"
    )


# ============================================================================
# Property-Based Test: Draft Invoice CRUD Operations
# ============================================================================

@given(
    grand_total=st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("99999.99"),
        places=2
    ),
    invoice_type=st.sampled_from([InvoiceType.SALES, InvoiceType.PURCHASE]),
    operation=st.sampled_from(["create", "update", "delete"])
)
@settings(
    max_examples=5,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None
)
def test_property_draft_invoice_operations_no_journal_entries(
    db_session: Session,
    mock_current_user,
    sample_customer,
    sample_supplier,
    grand_total: Decimal,
    invoice_type: InvoiceType,
    operation: str
):
    """
    Property-Based Test: For all invoices with status "draft", CRUD operations
    do not create journal entries.
    
    **EXPECTED OUTCOME**: This test PASSES on unfixed code (preservation test)
    **Validates: Requirements 3.6, 3.7, 3.8**
    """
    org_id = mock_current_user.organization_id
    service = InvoiceService(db_session)
    
    # Select party based on invoice type
    if invoice_type == InvoiceType.SALES:
        party_id = sample_customer.id
        party_type = "Customer"
    else:
        party_id = sample_supplier.id
        party_type = "Supplier"
    
    invoice_id = None
    invoice_no = f"INV-PBT-{uuid.uuid4().hex[:8].upper()}"
    
    try:
        if operation == "create":
            # Test: Create draft invoice
            invoice = Invoice(
                id=uuid.uuid4(),
                organization_id=org_id,
                invoice_no=invoice_no,
                invoice_type=invoice_type.value,
                party_id=party_id,
                party_type=party_type,
                posting_date=datetime.now(UTC),
                status=InvoiceStatus.DRAFT.value,
                grand_total=grand_total,
                currency="USD",
                created_by=mock_current_user.id,
                updated_by=mock_current_user.id,
            )
            db_session.add(invoice)
            db_session.commit()
            db_session.refresh(invoice)
            invoice_id = invoice.id
            
        elif operation == "update":
            # Test: Update draft invoice
            # First create a draft invoice
            invoice = Invoice(
                id=uuid.uuid4(),
                organization_id=org_id,
                invoice_no=invoice_no,
                invoice_type=invoice_type.value,
                party_id=party_id,
                party_type=party_type,
                posting_date=datetime.now(UTC),
                status=InvoiceStatus.DRAFT.value,
                grand_total=grand_total,
                currency="USD",
                created_by=mock_current_user.id,
                updated_by=mock_current_user.id,
            )
            db_session.add(invoice)
            db_session.commit()
            db_session.refresh(invoice)
            invoice_id = invoice.id
            
            # Update the invoice
            service.update(
                invoice_id=invoice_id,
                data={
                    "grand_total": grand_total + Decimal("100.00"),
                    "remarks": "Updated by property test",
                },
                organization_id=org_id,
                user_id=mock_current_user.id,
            )
            
        else:  # delete
            # Test: Delete draft invoice
            # First create a draft invoice
            invoice = Invoice(
                id=uuid.uuid4(),
                organization_id=org_id,
                invoice_no=invoice_no,
                invoice_type=invoice_type.value,
                party_id=party_id,
                party_type=party_type,
                posting_date=datetime.now(UTC),
                status=InvoiceStatus.DRAFT.value,
                grand_total=grand_total,
                currency="USD",
                created_by=mock_current_user.id,
                updated_by=mock_current_user.id,
            )
            db_session.add(invoice)
            db_session.commit()
            db_session.refresh(invoice)
            invoice_id = invoice.id
            
            # Delete the invoice
            service.delete(
                invoice_id=invoice_id,
                organization_id=org_id,
            )
        
        # Property: No journal entries should exist for draft invoice operations
        if invoice_id:
            journal_entries = db_session.query(JournalEntry).filter(
                JournalEntry.reference_type == "Invoice",
                JournalEntry.reference_id == invoice_id,
                JournalEntry.organization_id == org_id
            ).all()
            
            assert len(journal_entries) == 0, (
                f"Draft invoice {invoice_no} (type={invoice_type.value}, "
                f"operation={operation}, grand_total={grand_total}) should NOT "
                f"create journal entries. Found {len(journal_entries)} entries."
            )
        
    finally:
        # Cleanup: Delete invoice if it still exists (for create and update operations)
        if invoice_id and operation != "delete":
            try:
                invoice = db_session.query(Invoice).filter(Invoice.id == invoice_id).first()
                if invoice:
                    db_session.delete(invoice)
                    db_session.commit()
            except Exception:
                db_session.rollback()
