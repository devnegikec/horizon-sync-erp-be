"""Tests for PaymentEntryService cancel_payment method"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.base import (
    PaymentAuditAction,
    PaymentEntryStatus,
    PaymentSource,
)
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.payment_entry import PaymentEntry
from app.models.payment_reference import PaymentReference
from app.repositories.payment_audit_log_repository import PaymentAuditLogRepository
from app.repositories.payment_reference_repository import PaymentReferenceRepository
from app.services.payment_entry_service import PaymentEntryService


class TestCancelPayment:
    """Test suite for cancel_payment method"""

    def test_cancel_confirmed_payment_with_valid_reason(self, db_session: Session):
        """Test cancelling a confirmed payment with valid reason"""
        # Arrange
        org_id = uuid4()
        user_id = uuid4()

        # Create customer
        customer = Customer(
            id=uuid4(),
            organization_id=org_id,
            customer_name="Test Customer",
            customer_code="CUST001",
            email="test@example.com",
        )
        db_session.add(customer)
        db_session.commit()

        # Create confirmed payment entry
        payment_entry = PaymentEntry(
            id=uuid4(),
            organization_id=org_id,
            payment_type="Customer_Payment",
            party_id=customer.id,
            amount=Decimal("1000.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            payment_mode="Bank_Transfer",
            reference_no="UTR123456",
            status=PaymentEntryStatus.CONFIRMED,
            source=PaymentSource.MANUAL,
            receipt_number="RCP-2024-00001",
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment_entry)
        db_session.commit()

        service = PaymentEntryService(db_session)
        cancellation_reason = "Customer requested refund"

        # Act
        result = service.cancel_payment(
            payment_id=payment_entry.id,
            cancellation_reason=cancellation_reason,
            organization_id=org_id,
            user_id=user_id,
        )

        # Assert
        assert result.status == PaymentEntryStatus.CANCELLED.value
        assert result.cancellation_reason == cancellation_reason
        assert result.cancelled_by == user_id
        assert result.cancelled_at is not None

        # Verify audit log entry created
        audit_repo = PaymentAuditLogRepository(db_session)
        audit_logs = audit_repo.get_by_payment_id(payment_entry.id, org_id)
        cancel_logs = [
            log for log in audit_logs if log.action == PaymentAuditAction.CANCEL
        ]
        assert len(cancel_logs) == 1
        assert cancel_logs[0].new_values["cancellation_reason"] == cancellation_reason

    def test_cancel_payment_fails_when_not_confirmed(self, db_session: Session):
        """Test that cancellation fails when payment is not in Confirmed status"""
        # Arrange
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

        # Create draft payment entry
        payment_entry = PaymentEntry(
            id=uuid4(),
            organization_id=org_id,
            payment_type="Customer_Payment",
            party_id=customer.id,
            amount=Decimal("1000.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            payment_mode="Cash",
            status=PaymentEntryStatus.DRAFT,
            source=PaymentSource.MANUAL,
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment_entry)
        db_session.commit()

        service = PaymentEntryService(db_session)
        cancellation_reason = "Test cancellation"

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service.cancel_payment(
                payment_id=payment_entry.id,
                cancellation_reason=cancellation_reason,
                organization_id=org_id,
                user_id=user_id,
            )

        assert "Only Confirmed payments can be cancelled" in str(exc_info.value)

    def test_cancel_payment_fails_when_reason_empty(self, db_session: Session):
        """Test that cancellation fails when cancellation_reason is empty"""
        # Arrange
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
            payment_type="Customer_Payment",
            party_id=customer.id,
            amount=Decimal("1000.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            payment_mode="Bank_Transfer",
            reference_no="UTR123456",
            status=PaymentEntryStatus.CONFIRMED,
            source=PaymentSource.MANUAL,
            receipt_number="RCP-2024-00001",
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment_entry)
        db_session.commit()

        service = PaymentEntryService(db_session)

        # Act & Assert - Test with empty string
        with pytest.raises(ValidationError) as exc_info:
            service.cancel_payment(
                payment_id=payment_entry.id,
                cancellation_reason="",
                organization_id=org_id,
                user_id=user_id,
            )

        assert "Cancellation reason is required" in str(exc_info.value)

        # Act & Assert - Test with whitespace only
        with pytest.raises(ValidationError) as exc_info:
            service.cancel_payment(
                payment_id=payment_entry.id,
                cancellation_reason="   ",
                organization_id=org_id,
                user_id=user_id,
            )

        assert "Cancellation reason is required" in str(exc_info.value)

    def test_cancel_payment_removes_all_payment_references(self, db_session: Session):
        """Test that cancellation removes all payment references"""
        # Arrange
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

        # Create invoice with correct field name
        invoice = Invoice(
            id=uuid4(),
            organization_id=org_id,
            party_id=customer.id,  # Use party_id instead of customer_id
            party_type="Customer",
            invoice_no="INV-001",
            invoice_type="Sales",
            posting_date=datetime.now(UTC),
            grand_total=Decimal("1000.00"),
            outstanding_amount=Decimal("1000.00"),
            status="draft",
        )
        db_session.add(invoice)
        db_session.commit()

        # Create confirmed payment entry
        payment_entry = PaymentEntry(
            id=uuid4(),
            organization_id=org_id,
            payment_type="Customer_Payment",
            party_id=customer.id,
            amount=Decimal("1000.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            payment_mode="Bank_Transfer",
            reference_no="UTR123456",
            status=PaymentEntryStatus.CONFIRMED,
            source=PaymentSource.MANUAL,
            receipt_number="RCP-2024-00001",
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment_entry)
        db_session.commit()

        # Create payment reference
        payment_ref = PaymentReference(
            id=uuid4(),
            organization_id=org_id,
            payment_id=payment_entry.id,
            invoice_id=invoice.id,
            allocated_amount=Decimal("500.00"),
            exchange_rate=Decimal("1.0"),
            allocated_amount_invoice_currency=Decimal("500.00"),
            created_by=user_id,
        )
        db_session.add(payment_ref)
        db_session.commit()

        service = PaymentEntryService(db_session)
        cancellation_reason = "Payment error"

        # Verify references exist before cancellation
        reference_repo = PaymentReferenceRepository(db_session)
        references_before = reference_repo.get_by_payment_id(payment_entry.id, org_id)
        assert len(references_before) == 1

        # Act
        result = service.cancel_payment(
            payment_id=payment_entry.id,
            cancellation_reason=cancellation_reason,
            organization_id=org_id,
            user_id=user_id,
        )

        # Assert
        references_after = reference_repo.get_by_payment_id(payment_entry.id, org_id)
        assert len(references_after) == 0

    def test_cancel_payment_creates_audit_log_with_reason(self, db_session: Session):
        """Test that cancellation creates audit log entry with reason"""
        # Arrange
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
            payment_type="Customer_Payment",
            party_id=customer.id,
            amount=Decimal("1000.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            payment_mode="Bank_Transfer",
            reference_no="UTR123456",
            status=PaymentEntryStatus.CONFIRMED,
            source=PaymentSource.MANUAL,
            receipt_number="RCP-2024-00001",
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment_entry)
        db_session.commit()

        service = PaymentEntryService(db_session)
        cancellation_reason = "Customer dispute"

        # Act
        result = service.cancel_payment(
            payment_id=payment_entry.id,
            cancellation_reason=cancellation_reason,
            organization_id=org_id,
            user_id=user_id,
        )

        # Assert
        audit_repo = PaymentAuditLogRepository(db_session)
        audit_logs = audit_repo.get_by_payment_id(payment_entry.id, org_id)
        cancel_logs = [
            log for log in audit_logs if log.action == PaymentAuditAction.CANCEL
        ]

        assert len(cancel_logs) == 1
        assert cancel_logs[0].action == PaymentAuditAction.CANCEL
        assert cancel_logs[0].user_id == user_id
        assert cancel_logs[0].new_values["cancellation_reason"] == cancellation_reason
        assert cancel_logs[0].new_values["status"] == PaymentEntryStatus.CANCELLED.value
        assert cancel_logs[0].old_values["status"] == PaymentEntryStatus.CONFIRMED.value

    def test_cancel_payment_fails_for_nonexistent_payment(self, db_session: Session):
        """Test that cancellation fails for non-existent payment"""
        # Arrange
        org_id = uuid4()
        user_id = uuid4()
        service = PaymentEntryService(db_session)
        payment_id = uuid4()  # Non-existent ID
        cancellation_reason = "Test"

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service.cancel_payment(
                payment_id=payment_id,
                cancellation_reason=cancellation_reason,
                organization_id=org_id,
                user_id=user_id,
            )

        assert "not found" in str(exc_info.value).lower()

    def test_cancel_payment_trims_whitespace_from_reason(self, db_session: Session):
        """Test that cancellation trims whitespace from reason"""
        # Arrange
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
            payment_type="Customer_Payment",
            party_id=customer.id,
            amount=Decimal("1000.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            payment_mode="Bank_Transfer",
            reference_no="UTR123456",
            status=PaymentEntryStatus.CONFIRMED,
            source=PaymentSource.MANUAL,
            receipt_number="RCP-2024-00001",
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment_entry)
        db_session.commit()

        service = PaymentEntryService(db_session)
        cancellation_reason = "  Reason with spaces  "

        # Act
        result = service.cancel_payment(
            payment_id=payment_entry.id,
            cancellation_reason=cancellation_reason,
            organization_id=org_id,
            user_id=user_id,
        )

        # Assert
        assert result.cancellation_reason == "Reason with spaces"
