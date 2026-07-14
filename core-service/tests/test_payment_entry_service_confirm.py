"""Tests for PaymentEntryService confirm_payment() method"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.payment_reference import PaymentReference
from app.schemas.payment_entry import PaymentEntryCreate
from app.services.payment_entry_service import PaymentEntryService


@pytest.fixture
def setup_test_data(db_session: Session):
    """Setup test data for payment confirmation tests"""
    org_id = uuid4()
    user_id = uuid4()

    # Create customer
    customer = Customer(
        id=uuid4(),
        organization_id=org_id,
        customer_name="Test Customer",
        customer_code="CUST001",
        email="customer@example.com",
    )
    db_session.add(customer)

    # Create invoice
    invoice = Invoice(
        id=uuid4(),
        organization_id=org_id,
        customer_id=customer.id,
        invoice_number="INV-001",
        invoice_date=datetime.now(UTC),
        total_amount=Decimal("1000.00"),
        outstanding_balance=Decimal("1000.00"),
        status="Unpaid",
    )
    db_session.add(invoice)

    db_session.commit()

    return {
        "org_id": org_id,
        "user_id": user_id,
        "customer": customer,
        "invoice": invoice,
    }


@patch("app.services.payment_entry_service.JournalPostingService")
def test_confirm_payment_with_valid_data(
    mock_journal_service, db_session: Session, setup_test_data
):
    """Test confirm payment with valid payment and allocations"""
    data = setup_test_data

    # Mock journal posting service
    mock_journal_instance = Mock()
    mock_journal_service.return_value = mock_journal_instance
    mock_journal_instance._validate_default_accounts_configured.return_value = None
    mock_journal_instance.post_payment_journal_entry.return_value = {"id": uuid4()}

    service = PaymentEntryService(db_session)

    # Create payment entry
    payment_data = PaymentEntryCreate(
        payment_type="Customer_Payment",
        party_id=data["customer"].id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode="Bank_Transfer",
        reference_no="UTR123456",
    )

    payment = service.create_payment_entry(
        data=payment_data,
        organization_id=data["org_id"],
        user_id=data["user_id"],
    )

    # Create allocation
    allocation = PaymentReference(
        id=uuid4(),
        organization_id=data["org_id"],
        payment_id=payment.id,
        invoice_id=data["invoice"].id,
        allocated_amount=Decimal("1000.00"),
        exchange_rate=Decimal("1.0"),
        allocated_amount_invoice_currency=Decimal("1000.00"),
        created_by=data["user_id"],
        created_at=datetime.now(UTC),
    )
    db_session.add(allocation)
    db_session.commit()

    # Confirm payment
    confirmed = service.confirm_payment(
        payment_id=payment.id,
        organization_id=data["org_id"],
        user_id=data["user_id"],
    )

    # Assertions
    assert confirmed.status == "Confirmed"
    assert confirmed.receipt_number is not None
    assert confirmed.receipt_number.startswith("RCP-")
    assert str(datetime.now(UTC).year) in confirmed.receipt_number


@patch("app.services.payment_entry_service.JournalPostingService")
def test_confirm_payment_fails_when_not_draft(
    mock_journal_service, db_session: Session, setup_test_data
):
    """Test confirm fails when payment is not in Draft status"""
    data = setup_test_data

    # Mock journal posting service
    mock_journal_instance = Mock()
    mock_journal_service.return_value = mock_journal_instance
    mock_journal_instance._validate_default_accounts_configured.return_value = None
    mock_journal_instance.post_payment_journal_entry.return_value = {"id": uuid4()}

    service = PaymentEntryService(db_session)

    # Create payment entry
    payment_data = PaymentEntryCreate(
        payment_type="Customer_Payment",
        party_id=data["customer"].id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode="Bank_Transfer",
        reference_no="UTR123456",
    )

    payment = service.create_payment_entry(
        data=payment_data,
        organization_id=data["org_id"],
        user_id=data["user_id"],
    )

    # Create allocation
    allocation = PaymentReference(
        id=uuid4(),
        organization_id=data["org_id"],
        payment_id=payment.id,
        invoice_id=data["invoice"].id,
        allocated_amount=Decimal("1000.00"),
        exchange_rate=Decimal("1.0"),
        allocated_amount_invoice_currency=Decimal("1000.00"),
        created_by=data["user_id"],
        created_at=datetime.now(UTC),
    )
    db_session.add(allocation)
    db_session.commit()

    # Confirm payment first time
    service.confirm_payment(
        payment_id=payment.id,
        organization_id=data["org_id"],
        user_id=data["user_id"],
    )

    # Try to confirm again - should fail
    with pytest.raises(ValidationError) as exc_info:
        service.confirm_payment(
            payment_id=payment.id,
            organization_id=data["org_id"],
            user_id=data["user_id"],
        )

    assert "Only Draft payments can be confirmed" in str(exc_info.value)


def test_confirm_payment_fails_when_no_allocations(
    db_session: Session, setup_test_data
):
    """Test confirm fails when no allocations exist"""
    data = setup_test_data
    service = PaymentEntryService(db_session)

    # Create payment entry without allocations
    payment_data = PaymentEntryCreate(
        payment_type="Customer_Payment",
        party_id=data["customer"].id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode="Bank_Transfer",
        reference_no="UTR123456",
    )

    payment = service.create_payment_entry(
        data=payment_data,
        organization_id=data["org_id"],
        user_id=data["user_id"],
    )

    # Try to confirm without allocations - should fail
    with pytest.raises(ValidationError) as exc_info:
        service.confirm_payment(
            payment_id=payment.id,
            organization_id=data["org_id"],
            user_id=data["user_id"],
        )

    assert "Cannot confirm payment without allocations" in str(exc_info.value)


@patch("app.services.payment_entry_service.JournalPostingService")
def test_receipt_number_generation_is_unique(
    mock_journal_service, db_session: Session, setup_test_data
):
    """Test receipt number generation is unique"""
    data = setup_test_data

    # Mock journal posting service
    mock_journal_instance = Mock()
    mock_journal_service.return_value = mock_journal_instance
    mock_journal_instance._validate_default_accounts_configured.return_value = None
    mock_journal_instance.post_payment_journal_entry.return_value = {"id": uuid4()}

    service = PaymentEntryService(db_session)

    receipt_numbers = []

    # Create and confirm multiple payments
    for i in range(3):
        # Create payment entry
        payment_data = PaymentEntryCreate(
            payment_type="Customer_Payment",
            party_id=data["customer"].id,
            amount=Decimal("1000.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            payment_mode="Bank_Transfer",
            reference_no=f"UTR{i}",
        )

        payment = service.create_payment_entry(
            data=payment_data,
            organization_id=data["org_id"],
            user_id=data["user_id"],
        )

        # Create allocation
        allocation = PaymentReference(
            id=uuid4(),
            organization_id=data["org_id"],
            payment_id=payment.id,
            invoice_id=data["invoice"].id,
            allocated_amount=Decimal("100.00"),
            exchange_rate=Decimal("1.0"),
            allocated_amount_invoice_currency=Decimal("100.00"),
            created_by=data["user_id"],
            created_at=datetime.now(UTC),
        )
        db_session.add(allocation)
        db_session.commit()

        # Confirm payment
        confirmed = service.confirm_payment(
            payment_id=payment.id,
            organization_id=data["org_id"],
            user_id=data["user_id"],
        )

        receipt_numbers.append(confirmed.receipt_number)

    # Verify all receipt numbers are unique
    assert len(receipt_numbers) == len(set(receipt_numbers))

    # Verify they follow the expected format and sequence
    year = datetime.now(UTC).year
    assert receipt_numbers[0] == f"RCP-{year}-00001"
    assert receipt_numbers[1] == f"RCP-{year}-00002"
    assert receipt_numbers[2] == f"RCP-{year}-00003"


@patch("app.services.payment_entry_service.JournalPostingService")
def test_confirm_creates_audit_log_entry(
    mock_journal_service, db_session: Session, setup_test_data
):
    """Test audit log entry is created on confirmation"""
    data = setup_test_data

    # Mock journal posting service
    mock_journal_instance = Mock()
    mock_journal_service.return_value = mock_journal_instance
    mock_journal_instance._validate_default_accounts_configured.return_value = None
    mock_journal_instance.post_payment_journal_entry.return_value = {"id": uuid4()}

    service = PaymentEntryService(db_session)

    # Create payment entry
    payment_data = PaymentEntryCreate(
        payment_type="Customer_Payment",
        party_id=data["customer"].id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode="Bank_Transfer",
        reference_no="UTR123456",
    )

    payment = service.create_payment_entry(
        data=payment_data,
        organization_id=data["org_id"],
        user_id=data["user_id"],
    )

    # Create allocation
    allocation = PaymentReference(
        id=uuid4(),
        organization_id=data["org_id"],
        payment_id=payment.id,
        invoice_id=data["invoice"].id,
        allocated_amount=Decimal("1000.00"),
        exchange_rate=Decimal("1.0"),
        allocated_amount_invoice_currency=Decimal("1000.00"),
        created_by=data["user_id"],
        created_at=datetime.now(UTC),
    )
    db_session.add(allocation)
    db_session.commit()

    # Confirm payment
    service.confirm_payment(
        payment_id=payment.id,
        organization_id=data["org_id"],
        user_id=data["user_id"],
    )

    # Verify audit log entry exists
    from app.models.base import PaymentAuditAction
    from app.models.payment_audit_log import PaymentAuditLog

    audit_logs = (
        db_session.query(PaymentAuditLog)
        .filter(
            PaymentAuditLog.payment_id == payment.id,
            PaymentAuditLog.action == PaymentAuditAction.CONFIRM,
        )
        .all()
    )

    assert len(audit_logs) == 1
    audit_log = audit_logs[0]
    assert audit_log.user_id == data["user_id"]
    assert audit_log.old_values["status"] == "Draft"
    assert audit_log.new_values["status"] == "Confirmed"
    assert audit_log.new_values["receipt_number"] is not None


@patch("app.services.payment_entry_service.JournalPostingService")
def test_confirm_fails_when_default_accounts_not_configured(
    mock_journal_service, db_session: Session, setup_test_data
):
    """Test confirm fails when default accounts not configured"""
    data = setup_test_data

    # Mock journal posting service to raise validation error
    mock_journal_instance = Mock()
    mock_journal_service.return_value = mock_journal_instance
    mock_journal_instance._validate_default_accounts_configured.side_effect = (
        ValidationError("Default account for 'bank' not configured")
    )

    service = PaymentEntryService(db_session)

    # Create payment entry
    payment_data = PaymentEntryCreate(
        payment_type="Customer_Payment",
        party_id=data["customer"].id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode="Bank_Transfer",
        reference_no="UTR123456",
    )

    payment = service.create_payment_entry(
        data=payment_data,
        organization_id=data["org_id"],
        user_id=data["user_id"],
    )

    # Create allocation
    allocation = PaymentReference(
        id=uuid4(),
        organization_id=data["org_id"],
        payment_id=payment.id,
        invoice_id=data["invoice"].id,
        allocated_amount=Decimal("1000.00"),
        exchange_rate=Decimal("1.0"),
        allocated_amount_invoice_currency=Decimal("1000.00"),
        created_by=data["user_id"],
        created_at=datetime.now(UTC),
    )
    db_session.add(allocation)
    db_session.commit()

    # Try to confirm - should fail
    with pytest.raises(ValidationError) as exc_info:
        service.confirm_payment(
            payment_id=payment.id,
            organization_id=data["org_id"],
            user_id=data["user_id"],
        )

    assert "Cannot confirm payment" in str(exc_info.value)
    assert "Default account" in str(exc_info.value)
