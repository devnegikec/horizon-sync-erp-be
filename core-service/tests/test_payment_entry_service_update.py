"""Test for PaymentEntryService.update_payment_entry() method"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.exceptions import ValidationError
from app.models.base import (
    PaymentEntryStatus,
    PaymentEntryType,
    PaymentMode,
    PaymentSource,
)
from app.models.customer import Customer
from app.models.payment_entry import PaymentEntry
from app.schemas.payment_entry import PaymentEntryUpdate
from app.services.payment_entry_service import PaymentEntryService


def test_update_payment_entry_success(db_session):
    """Test successful payment entry update"""
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

    # Update payment entry
    update_data = PaymentEntryUpdate(
        amount=Decimal("1500.00"),
        payment_mode="Check",
        reference_no="CHK-789",
    )

    service = PaymentEntryService(db_session)
    result = service.update_payment_entry(
        payment_entry.id, update_data, org_id, user_id
    )

    # Verify updated fields
    assert result.amount == Decimal("1500.00")
    assert result.payment_mode == "Check"
    assert result.reference_no == "CHK-789"

    # Verify unchanged fields
    assert result.payment_type == "Customer_Payment"
    assert result.party_id == customer.id
    assert result.currency_code == "USD"
    assert result.status == PaymentEntryStatus.DRAFT.value

    # Verify updated_by was set
    assert result.updated_by == user_id


def test_update_payment_entry_amount_only(db_session):
    """Test updating only the amount field"""
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

    # Update only amount
    update_data = PaymentEntryUpdate(amount=Decimal("2000.00"))

    service = PaymentEntryService(db_session)
    result = service.update_payment_entry(
        payment_entry.id, update_data, org_id, user_id
    )

    assert result.amount == Decimal("2000.00")
    assert result.payment_mode == "Cash"  # Unchanged


def test_update_payment_entry_not_draft(db_session):
    """Test that confirmed payments cannot be updated"""
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

    # Try to update
    update_data = PaymentEntryUpdate(amount=Decimal("2000.00"))

    service = PaymentEntryService(db_session)
    with pytest.raises(ValidationError, match="Only Draft payments can be updated"):
        service.update_payment_entry(payment_entry.id, update_data, org_id, user_id)


def test_update_payment_entry_not_found(db_session):
    """Test updating non-existent payment entry"""
    org_id = uuid4()
    user_id = uuid4()

    update_data = PaymentEntryUpdate(amount=Decimal("2000.00"))

    service = PaymentEntryService(db_session)
    with pytest.raises(
        ValidationError, match="not found or does not belong to organization"
    ):
        service.update_payment_entry(uuid4(), update_data, org_id, user_id)


def test_update_payment_entry_invalid_amount(db_session):
    """Test updating with invalid amount (Pydantic validation)"""
    from pydantic import ValidationError as PydanticValidationError

    # Try to create update data with amount having too many decimal places
    # This should be caught by Pydantic validation
    with pytest.raises(PydanticValidationError, match="at most 2 decimal places"):
        update_data = PaymentEntryUpdate(amount=Decimal("1000.123"))


def test_update_payment_entry_cash_limit_exceeded(db_session):
    """Test updating cash payment with amount exceeding limit"""
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

    # Try to update with amount exceeding cash limit
    update_data = PaymentEntryUpdate(amount=Decimal("15000.00"))

    service = PaymentEntryService(db_session)
    with pytest.raises(ValidationError, match="exceeds maximum limit"):
        service.update_payment_entry(payment_entry.id, update_data, org_id, user_id)


def test_update_payment_entry_payment_date(db_session):
    """Test updating payment date"""
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

    # Update payment date to tomorrow
    new_date = datetime.now(UTC) + timedelta(days=1)
    update_data = PaymentEntryUpdate(payment_date=new_date)

    service = PaymentEntryService(db_session)
    result = service.update_payment_entry(
        payment_entry.id, update_data, org_id, user_id
    )

    # Verify date was updated (compare dates only, not exact timestamps)
    assert result.payment_date.date() == new_date.date()


def test_update_payment_entry_invalid_future_date(db_session):
    """Test updating with payment date too far in future (Pydantic validation)"""
    from pydantic import ValidationError as PydanticValidationError

    # Try to create update data with date more than 30 days in future
    # This should be caught by Pydantic validation
    future_date = datetime.now(UTC) + timedelta(days=31)
    with pytest.raises(
        PydanticValidationError, match="cannot be more than 30 days in the future"
    ):
        update_data = PaymentEntryUpdate(payment_date=future_date)


def test_update_payment_entry_audit_log_created(db_session):
    """Test that audit log is created on update"""
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

    # Update payment entry
    update_data = PaymentEntryUpdate(amount=Decimal("2000.00"))

    service = PaymentEntryService(db_session)
    result = service.update_payment_entry(
        payment_entry.id, update_data, org_id, user_id
    )

    # Verify audit log was created
    from app.models.base import PaymentAuditAction
    from app.models.payment_audit_log import PaymentAuditLog

    audit_logs = (
        db_session.query(PaymentAuditLog)
        .filter(
            PaymentAuditLog.payment_id == payment_entry.id,
            PaymentAuditLog.action == PaymentAuditAction.UPDATE,
        )
        .all()
    )

    assert len(audit_logs) == 1
    audit_log = audit_logs[0]
    assert audit_log.user_id == user_id
    assert audit_log.old_values is not None
    assert audit_log.new_values is not None
    assert audit_log.old_values["amount"] == "1000.00"
    assert audit_log.new_values["amount"] == "2000.00"
