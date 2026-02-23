"""Test for PaymentEntryService.delete_payment_entry() method"""

import pytest
from datetime import datetime, UTC
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.base import PaymentEntryStatus, PaymentSource, PaymentEntryType, PaymentMode
from app.models.customer import Customer
from app.models.payment_entry import PaymentEntry
from app.services.payment_entry_service import PaymentEntryService


def test_delete_payment_entry_success(db_session):
    """Test successful deletion of draft payment entry"""
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
    
    # Create payment entry in Draft status
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
    
    payment_id = payment_entry.id
    
    # Delete payment entry
    service = PaymentEntryService(db_session)
    service.delete_payment_entry(payment_id, org_id)
    
    # Verify payment entry was deleted
    deleted_payment = db_session.query(PaymentEntry).filter(
        PaymentEntry.id == payment_id
    ).first()
    
    assert deleted_payment is None


def test_delete_payment_entry_not_draft(db_session):
    """Test that confirmed payments cannot be deleted"""
    org_id = uuid4()
    user_id = uuid4()
    
    customer = Customer(
        id=uuid4(),
        organization_id=org_id,
        customer_name="Test Customer",
        customer_code="CUST001",
        email="test@example.com",
    )
    db_session.add(customer)
    db_session.commit()
    
    # Create payment entry in Confirmed status
    payment_entry = PaymentEntry(
        id=uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=customer.id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.CONFIRMED,  # Not Draft
        source=PaymentSource.MANUAL,
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(payment_entry)
    db_session.commit()
    
    # Try to delete
    service = PaymentEntryService(db_session)
    with pytest.raises(ValidationError, match="Only Draft payments can be deleted"):
        service.delete_payment_entry(payment_entry.id, org_id)
    
    # Verify payment entry still exists
    existing_payment = db_session.query(PaymentEntry).filter(
        PaymentEntry.id == payment_entry.id
    ).first()
    
    assert existing_payment is not None


def test_delete_payment_entry_cancelled_status(db_session):
    """Test that cancelled payments cannot be deleted"""
    org_id = uuid4()
    user_id = uuid4()
    
    customer = Customer(
        id=uuid4(),
        organization_id=org_id,
        customer_name="Test Customer",
        customer_code="CUST001",
        email="test@example.com",
    )
    db_session.add(customer)
    db_session.commit()
    
    # Create payment entry in Cancelled status
    payment_entry = PaymentEntry(
        id=uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=customer.id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.CANCELLED,  # Cancelled
        source=PaymentSource.MANUAL,
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(payment_entry)
    db_session.commit()
    
    # Try to delete
    service = PaymentEntryService(db_session)
    with pytest.raises(ValidationError, match="Only Draft payments can be deleted"):
        service.delete_payment_entry(payment_entry.id, org_id)


def test_delete_payment_entry_not_found(db_session):
    """Test deleting non-existent payment entry"""
    org_id = uuid4()
    
    service = PaymentEntryService(db_session)
    with pytest.raises(ValidationError, match="not found or does not belong to organization"):
        service.delete_payment_entry(uuid4(), org_id)


def test_delete_payment_entry_wrong_organization(db_session):
    """Test deleting payment entry from different organization"""
    org_id = uuid4()
    other_org_id = uuid4()
    user_id = uuid4()
    
    customer = Customer(
        id=uuid4(),
        organization_id=org_id,
        customer_name="Test Customer",
        customer_code="CUST001",
        email="test@example.com",
    )
    db_session.add(customer)
    db_session.commit()
    
    # Create payment entry for org_id
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
    
    # Try to delete with different organization_id
    service = PaymentEntryService(db_session)
    with pytest.raises(ValidationError, match="not found or does not belong to organization"):
        service.delete_payment_entry(payment_entry.id, other_org_id)
    
    # Verify payment entry still exists
    existing_payment = db_session.query(PaymentEntry).filter(
        PaymentEntry.id == payment_entry.id
    ).first()
    
    assert existing_payment is not None


def test_delete_payment_entry_with_audit_logs_cascade(db_session):
    """Test that deleting payment entry cascades to audit logs"""
    org_id = uuid4()
    user_id = uuid4()
    
    customer = Customer(
        id=uuid4(),
        organization_id=org_id,
        customer_name="Test Customer",
        customer_code="CUST001",
        email="test@example.com",
    )
    db_session.add(customer)
    db_session.commit()
    
    # Create payment entry in Draft status
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
    
    # Create an audit log entry
    from app.models.payment_audit_log import PaymentAuditLog
    from app.models.base import PaymentAuditAction
    
    audit_log = PaymentAuditLog(
        id=uuid4(),
        organization_id=org_id,
        payment_id=payment_entry.id,
        action=PaymentAuditAction.CREATE,
        user_id=user_id,
        old_values=None,
        new_values={"amount": "1000.00"},
        timestamp=datetime.now(UTC),
    )
    db_session.add(audit_log)
    db_session.commit()
    
    payment_id = payment_entry.id
    audit_log_id = audit_log.id
    
    # Delete payment entry
    service = PaymentEntryService(db_session)
    service.delete_payment_entry(payment_id, org_id)
    
    # Verify payment entry was deleted
    deleted_payment = db_session.query(PaymentEntry).filter(
        PaymentEntry.id == payment_id
    ).first()
    assert deleted_payment is None
    
    # Verify audit log was also deleted (cascade)
    deleted_audit = db_session.query(PaymentAuditLog).filter(
        PaymentAuditLog.id == audit_log_id
    ).first()
    assert deleted_audit is None
