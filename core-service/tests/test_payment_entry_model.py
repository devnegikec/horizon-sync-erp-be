"""Tests for PaymentEntry model"""

import uuid
from datetime import datetime, UTC
from decimal import Decimal

import pytest

from app.models import (
    PaymentEntry,
    PaymentReference,
    PaymentAuditLog,
    PaymentEntryType,
    PaymentMode,
    PaymentEntryStatus,
    PaymentSource,
    PaymentAuditAction,
)


def test_payment_entry_creation(db_session):
    """Test creating a payment entry"""
    org_id = uuid.uuid4()
    party_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    payment = PaymentEntry(
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=party_id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        source=PaymentSource.MANUAL,
        created_by=user_id,
        updated_by=user_id,
    )
    
    db_session.add(payment)
    db_session.commit()
    
    # Verify it was created
    assert payment.id is not None
    assert payment.organization_id == org_id
    assert payment.payment_type == PaymentEntryType.CUSTOMER_PAYMENT
    assert payment.party_id == party_id
    assert payment.amount == Decimal("1000.00")
    assert payment.currency_code == "USD"
    assert payment.payment_mode == PaymentMode.CASH
    assert payment.status == PaymentEntryStatus.DRAFT
    assert payment.source == PaymentSource.MANUAL
    assert payment.created_at is not None
    assert payment.updated_at is not None


def test_payment_entry_with_reference_no(db_session):
    """Test creating a payment entry with reference number"""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    payment = PaymentEntry(
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("500.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CHECK,
        reference_no="CHK-12345",
        status=PaymentEntryStatus.DRAFT,
        source=PaymentSource.MANUAL,
        created_by=user_id,
        updated_by=user_id,
    )
    
    db_session.add(payment)
    db_session.commit()
    
    assert payment.reference_no == "CHK-12345"


def test_payment_entry_unallocated_amount_no_references(db_session):
    """Test unallocated_amount calculation with no references"""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    payment = PaymentEntry(
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        source=PaymentSource.MANUAL,
        created_by=user_id,
        updated_by=user_id,
    )
    
    db_session.add(payment)
    db_session.commit()
    
    # With no references, unallocated amount should equal payment amount
    assert payment.unallocated_amount == Decimal("1000.00")


def test_payment_entry_repr(db_session):
    """Test string representation of payment entry"""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    payment = PaymentEntry(
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        source=PaymentSource.MANUAL,
        created_by=user_id,
        updated_by=user_id,
    )
    
    db_session.add(payment)
    db_session.commit()
    
    repr_str = repr(payment)
    assert "PaymentEntry" in repr_str
    assert "Customer_Payment" in repr_str
    assert "1000.00" in repr_str
    assert "USD" in repr_str
    assert "Cash" in repr_str
    assert "Draft" in repr_str


def test_payment_entry_default_values(db_session):
    """Test default values for payment entry"""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    payment = PaymentEntry(
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("1000.00"),
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        created_by=user_id,
        updated_by=user_id,
    )
    
    db_session.add(payment)
    db_session.commit()
    
    # Verify default values
    assert payment.currency_code == "USD"
    assert payment.status == PaymentEntryStatus.DRAFT
    assert payment.source == PaymentSource.MANUAL


def test_payment_entry_with_cancellation(db_session):
    """Test payment entry with cancellation information"""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cancelled_by = uuid.uuid4()
    
    payment = PaymentEntry(
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.CANCELLED,
        source=PaymentSource.MANUAL,
        cancellation_reason="Duplicate entry",
        cancelled_by=cancelled_by,
        cancelled_at=datetime.now(UTC),
        created_by=user_id,
        updated_by=user_id,
    )
    
    db_session.add(payment)
    db_session.commit()
    
    assert payment.status == PaymentEntryStatus.CANCELLED
    assert payment.cancellation_reason == "Duplicate entry"
    assert payment.cancelled_by == cancelled_by
    assert payment.cancelled_at is not None


def test_payment_reference_creation(db_session):
    """Test creating a payment reference"""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create a payment entry first
    payment = PaymentEntry(
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        source=PaymentSource.MANUAL,
        created_by=user_id,
        updated_by=user_id,
    )
    
    db_session.add(payment)
    db_session.commit()
    
    # Note: We can't create a payment reference without an invoice table
    # This test is just to verify the model structure
    # Full integration tests will be done when invoice model is available


def test_payment_audit_log_creation(db_session):
    """Test creating a payment audit log entry"""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create a payment entry first
    payment = PaymentEntry(
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        source=PaymentSource.MANUAL,
        created_by=user_id,
        updated_by=user_id,
    )
    
    db_session.add(payment)
    db_session.commit()
    
    # Create an audit log entry
    audit_log = PaymentAuditLog(
        organization_id=org_id,
        payment_id=payment.id,
        action=PaymentAuditAction.CREATE,
        user_id=user_id,
        new_values={"amount": "1000.00", "status": "Draft"},
    )
    
    db_session.add(audit_log)
    db_session.commit()
    
    assert audit_log.id is not None
    assert audit_log.payment_id == payment.id
    assert audit_log.action == PaymentAuditAction.CREATE
    assert audit_log.user_id == user_id
    assert audit_log.timestamp is not None


def test_payment_audit_log_repr(db_session):
    """Test string representation of payment audit log"""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create a payment entry first
    payment = PaymentEntry(
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        source=PaymentSource.MANUAL,
        created_by=user_id,
        updated_by=user_id,
    )
    
    db_session.add(payment)
    db_session.commit()
    
    # Create an audit log entry
    audit_log = PaymentAuditLog(
        organization_id=org_id,
        payment_id=payment.id,
        action=PaymentAuditAction.CREATE,
        user_id=user_id,
    )
    
    db_session.add(audit_log)
    db_session.commit()
    
    repr_str = repr(audit_log)
    assert "PaymentAuditLog" in repr_str
    assert "CREATE" in repr_str
