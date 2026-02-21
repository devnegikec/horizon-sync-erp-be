"""Tests for AllocationService.remove_allocation() method"""

import uuid
from decimal import Decimal
from datetime import datetime, UTC

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.base import PaymentEntryStatus, PaymentEntryType, PaymentMode, PaymentAuditAction
from app.models.payment_entry import PaymentEntry
from app.models.payment_reference import PaymentReference
from app.models.invoice import Invoice
from app.services.allocation_service import AllocationService
from app.repositories.payment_audit_log_repository import PaymentAuditLogRepository


@pytest.fixture
def test_organization_id():
    """Test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return uuid.uuid4()


def test_remove_allocation_success(db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID):
    """Test successful removal of payment allocation"""
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
    
    # Create allocation
    service = AllocationService(db_session)
    allocation = service.create_allocation(
        payment_id=payment.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("500.00"),
        organization_id=test_organization_id,
        user_id=test_user_id,
    )
    
    # Verify allocation exists
    assert allocation is not None
    allocation_id = allocation.id
    
    # Remove allocation
    service.remove_allocation(
        allocation_id=allocation_id,
        organization_id=test_organization_id,
        user_id=test_user_id,
    )
    
    # Verify allocation was deleted
    deleted_allocation = (
        db_session.query(PaymentReference)
        .filter(PaymentReference.id == allocation_id)
        .first()
    )
    assert deleted_allocation is None
    
    # Verify audit log entry was created
    audit_repo = PaymentAuditLogRepository(db_session)
    audit_logs = audit_repo.get_by_payment_id(payment.id, test_organization_id)
    
    # Should have 2 audit logs: ALLOCATE and DEALLOCATE
    assert len(audit_logs) >= 2
    
    # Find the DEALLOCATE audit log
    deallocate_log = next(
        (log for log in audit_logs if log.action == PaymentAuditAction.DEALLOCATE),
        None
    )
    assert deallocate_log is not None
    assert deallocate_log.old_values["invoice_id"] == str(invoice.id)
    assert deallocate_log.old_values["allocated_amount"] == "500.00"
    assert deallocate_log.new_values is None


def test_remove_allocation_payment_not_draft(db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID):
    """Test that allocation removal fails when payment is not in Draft status"""
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
        status=PaymentEntryStatus.DRAFT,
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
    
    # Create allocation
    service = AllocationService(db_session)
    allocation = service.create_allocation(
        payment_id=payment.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("500.00"),
        organization_id=test_organization_id,
        user_id=test_user_id,
    )
    allocation_id = allocation.id
    
    # Change payment status to Confirmed
    payment.status = PaymentEntryStatus.CONFIRMED
    db_session.commit()
    
    # Try to remove allocation - should fail
    with pytest.raises(ValidationError, match="Payment must be in Draft status"):
        service.remove_allocation(
            allocation_id=allocation_id,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )


def test_remove_allocation_not_found(db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID):
    """Test that allocation removal fails when allocation doesn't exist"""
    service = AllocationService(db_session)
    
    # Try to remove non-existent allocation
    with pytest.raises(ValidationError, match="not found or does not belong to organization"):
        service.remove_allocation(
            allocation_id=uuid.uuid4(),
            organization_id=test_organization_id,
            user_id=test_user_id,
        )


def test_remove_allocation_different_organization(db_session: Session, test_user_id: uuid.UUID):
    """Test that allocation removal fails when allocation belongs to different organization"""
    org1_id = uuid.uuid4()
    org2_id = uuid.uuid4()
    
    # Create a payment entry in org1
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
    
    # Create an invoice in org1
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org1_id,
        invoice_no="INV-003",
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
    
    # Create allocation in org1
    service = AllocationService(db_session)
    allocation = service.create_allocation(
        payment_id=payment.id,
        invoice_id=invoice.id,
        allocated_amount=Decimal("500.00"),
        organization_id=org1_id,
        user_id=test_user_id,
    )
    allocation_id = allocation.id
    
    # Try to remove allocation from org2 - should fail
    with pytest.raises(ValidationError, match="not found or does not belong to organization"):
        service.remove_allocation(
            allocation_id=allocation_id,
            organization_id=org2_id,  # Different organization
            user_id=test_user_id,
        )


def test_remove_allocation_updates_unallocated_amount(db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID):
    """Test that removing allocation updates payment unallocated amount"""
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
        invoice_no="INV-004",
        invoice_type="sales",
        party_id=payment.party_id,
        party_type="customer",
        grand_total=Decimal("400.00"),
        outstanding_amount=Decimal("400.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    invoice2 = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-005",
        invoice_type="sales",
        party_id=payment.party_id,
        party_type="customer",
        grand_total=Decimal("300.00"),
        outstanding_amount=Decimal("300.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(invoice1)
    db_session.add(invoice2)
    db_session.commit()
    
    # Create two allocations
    service = AllocationService(db_session)
    allocation1 = service.create_allocation(
        payment_id=payment.id,
        invoice_id=invoice1.id,
        allocated_amount=Decimal("400.00"),
        organization_id=test_organization_id,
        user_id=test_user_id,
    )
    allocation2 = service.create_allocation(
        payment_id=payment.id,
        invoice_id=invoice2.id,
        allocated_amount=Decimal("300.00"),
        organization_id=test_organization_id,
        user_id=test_user_id,
    )
    
    # Refresh payment to get updated unallocated_amount
    db_session.refresh(payment)
    
    # Verify unallocated amount is 300.00 (1000 - 400 - 300)
    assert payment.unallocated_amount == Decimal("300.00")
    
    # Remove first allocation
    service.remove_allocation(
        allocation_id=allocation1.id,
        organization_id=test_organization_id,
        user_id=test_user_id,
    )
    
    # Refresh payment to get updated unallocated_amount
    db_session.refresh(payment)
    
    # Verify unallocated amount is now 700.00 (1000 - 300)
    assert payment.unallocated_amount == Decimal("700.00")
    
    # Remove second allocation
    service.remove_allocation(
        allocation_id=allocation2.id,
        organization_id=test_organization_id,
        user_id=test_user_id,
    )
    
    # Refresh payment to get updated unallocated_amount
    db_session.refresh(payment)
    
    # Verify unallocated amount is now 1000.00 (full payment amount)
    assert payment.unallocated_amount == Decimal("1000.00")
