"""Tests for Payment Made service"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.models.base import InvoiceStatus, InvoiceType, PaymentType
from app.models.invoice import Invoice
from app.services.payment_made_service import PaymentMadeService


@pytest.fixture
def payment_made_service(db_session: Session):
    """Create PaymentMadeService instance"""
    return PaymentMadeService(db_session)


@pytest.fixture
def organization_id():
    """Create organization ID"""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Create user ID"""
    return uuid.uuid4()


@pytest.fixture
def supplier_id():
    """Create supplier ID"""
    return uuid.uuid4()


@pytest.fixture
def purchase_invoice(db_session: Session, organization_id: uuid.UUID, supplier_id: uuid.UUID):
    """Create a Purchase Invoice with outstanding balance"""
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=organization_id,
        invoice_no="PI-001",
        invoice_type=InvoiceType.PURCHASE,
        party_id=supplier_id,
        party_type="SUPPLIER",
        reference_type="PURCHASE_ORDER",
        reference_id=uuid.uuid4(),
        posting_date=datetime.now(UTC),
        status=InvoiceStatus.PENDING,
        grand_total=Decimal("1000.00"),
        outstanding_amount=Decimal("1000.00"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


class TestPaymentMadeService:
    """Tests for Payment Made service"""

    def test_create_payment_success(
        self,
        payment_made_service: PaymentMadeService,
        purchase_invoice: Invoice,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """Test successful payment creation"""
        # Arrange
        payment_amount = Decimal("500.00")
        payment_no = "PAY-001"

        # Act
        result = payment_made_service.create_payment(
            purchase_invoice_id=purchase_invoice.id,
            amount=payment_amount,
            organization_id=organization_id,
            user_id=user_id,
            payment_no=payment_no,
            posting_date=datetime.now(UTC),
            payment_method="bank_transfer",
            reference_no="REF-001",
            remarks="Payment for invoice PI-001",
        )

        # Assert
        assert result["id"] is not None
        assert result["payment_type"] == "pay"  # Requirement 7.1: payment_type is PAY
        assert result["party_type"] == "SUPPLIER"
        assert result["party_id"] == purchase_invoice.party_id
        assert result["amount"] == payment_amount
        assert result["payment_no"] == payment_no
        assert result["status"] == "pending"
        assert result["payment_method"] == "bank_transfer"
        assert result["reference_no"] == "REF-001"
        assert result["remarks"] == "Payment for invoice PI-001"
        # Requirement 7.2: reference_type and reference_id stored in extra_data
        assert result["reference_type"] == "PURCHASE_INVOICE"
        assert result["reference_id"] == str(purchase_invoice.id)

    def test_create_payment_invoice_not_found(
        self,
        payment_made_service: PaymentMadeService,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """Test payment creation with non-existent invoice"""
        # Arrange
        non_existent_invoice_id = uuid.uuid4()

        # Act & Assert
        # Requirement 7.3: Validate Purchase Invoice exists
        with pytest.raises(ResourceNotFoundException) as exc_info:
            payment_made_service.create_payment(
                purchase_invoice_id=non_existent_invoice_id,
                amount=Decimal("500.00"),
                organization_id=organization_id,
                user_id=user_id,
                payment_no="PAY-001",
            )

        assert str(non_existent_invoice_id) in str(exc_info.value)

    def test_create_payment_zero_outstanding_balance(
        self,
        payment_made_service: PaymentMadeService,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ):
        """Test payment creation with zero outstanding balance"""
        # Arrange - Create invoice with zero outstanding balance
        invoice = Invoice(
            id=uuid.uuid4(),
            organization_id=organization_id,
            invoice_no="PI-002",
            invoice_type=InvoiceType.PURCHASE,
            party_id=supplier_id,
            party_type="SUPPLIER",
            posting_date=datetime.now(UTC),
            status=InvoiceStatus.PAID,
            grand_total=Decimal("1000.00"),
            outstanding_amount=Decimal("0.00"),  # Zero balance
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(invoice)
        db_session.commit()

        # Act & Assert
        # Requirement 7.3: Validate outstanding balance > 0
        with pytest.raises(ValidationException) as exc_info:
            payment_made_service.create_payment(
                purchase_invoice_id=invoice.id,
                amount=Decimal("100.00"),
                organization_id=organization_id,
                user_id=user_id,
                payment_no="PAY-002",
            )

        assert "Outstanding balance is 0" in str(exc_info.value)
        assert "outstanding balance > 0" in str(exc_info.value)

    def test_create_payment_negative_amount(
        self,
        payment_made_service: PaymentMadeService,
        purchase_invoice: Invoice,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """Test payment creation with negative amount"""
        # Act & Assert
        with pytest.raises(ValidationException) as exc_info:
            payment_made_service.create_payment(
                purchase_invoice_id=purchase_invoice.id,
                amount=Decimal("-100.00"),
                organization_id=organization_id,
                user_id=user_id,
                payment_no="PAY-003",
            )

        assert "must be greater than zero" in str(exc_info.value)

    def test_create_payment_zero_amount(
        self,
        payment_made_service: PaymentMadeService,
        purchase_invoice: Invoice,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """Test payment creation with zero amount"""
        # Act & Assert
        with pytest.raises(ValidationException) as exc_info:
            payment_made_service.create_payment(
                purchase_invoice_id=purchase_invoice.id,
                amount=Decimal("0.00"),
                organization_id=organization_id,
                user_id=user_id,
                payment_no="PAY-004",
            )

        assert "must be greater than zero" in str(exc_info.value)

    def test_create_payment_exceeds_outstanding_balance(
        self,
        payment_made_service: PaymentMadeService,
        purchase_invoice: Invoice,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """Test payment creation with amount exceeding outstanding balance"""
        # Arrange
        outstanding_balance = purchase_invoice.outstanding_amount
        excessive_amount = outstanding_balance + Decimal("100.00")

        # Act & Assert
        with pytest.raises(ValidationException) as exc_info:
            payment_made_service.create_payment(
                purchase_invoice_id=purchase_invoice.id,
                amount=excessive_amount,
                organization_id=organization_id,
                user_id=user_id,
                payment_no="PAY-005",
            )

        assert "exceeds outstanding balance" in str(exc_info.value)

    def test_create_payment_partial_payment(
        self,
        payment_made_service: PaymentMadeService,
        purchase_invoice: Invoice,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """Test partial payment creation"""
        # Arrange
        partial_amount = Decimal("300.00")

        # Act
        result = payment_made_service.create_payment(
            purchase_invoice_id=purchase_invoice.id,
            amount=partial_amount,
            organization_id=organization_id,
            user_id=user_id,
            payment_no="PAY-006",
        )

        # Assert
        assert result["amount"] == partial_amount
        assert result["payment_type"] == "pay"

    def test_create_payment_full_payment(
        self,
        payment_made_service: PaymentMadeService,
        purchase_invoice: Invoice,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """Test full payment creation"""
        # Arrange
        full_amount = purchase_invoice.outstanding_amount

        # Act
        result = payment_made_service.create_payment(
            purchase_invoice_id=purchase_invoice.id,
            amount=full_amount,
            organization_id=organization_id,
            user_id=user_id,
            payment_no="PAY-007",
        )

        # Assert
        assert result["amount"] == full_amount
        assert result["payment_type"] == "pay"

    def test_create_payment_with_all_optional_fields(
        self,
        payment_made_service: PaymentMadeService,
        purchase_invoice: Invoice,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """Test payment creation with all optional fields"""
        # Act
        result = payment_made_service.create_payment(
            purchase_invoice_id=purchase_invoice.id,
            amount=Decimal("500.00"),
            organization_id=organization_id,
            user_id=user_id,
            payment_no="PAY-008",
            posting_date=datetime.now(UTC),
            payment_method="cash",
            reference_no="REF-008",
            remarks="Test payment with all fields",
        )

        # Assert
        assert result["payment_method"] == "cash"
        assert result["reference_no"] == "REF-008"
        assert result["remarks"] == "Test payment with all fields"
        assert result["posting_date"] is not None

    def test_partial_payment_reduces_balance(
        self,
        payment_made_service: PaymentMadeService,
        purchase_invoice: Invoice,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        db_session: Session,
    ):
        """
        Test that partial payment reduces outstanding balance but doesn't change status.
        
        Requirement 7.4: Reduce outstanding balance by payment amount
        """
        # Arrange
        initial_balance = purchase_invoice.outstanding_amount
        payment_amount = Decimal("300.00")
        expected_balance = initial_balance - payment_amount

        # Act
        payment_made_service.create_payment(
            purchase_invoice_id=purchase_invoice.id,
            amount=payment_amount,
            organization_id=organization_id,
            user_id=user_id,
            payment_no="PAY-009",
        )

        # Assert - Refresh invoice to get updated values
        db_session.refresh(purchase_invoice)
        assert purchase_invoice.outstanding_amount == expected_balance
        assert purchase_invoice.status == InvoiceStatus.PENDING  # Status unchanged

    def test_full_payment_updates_status_to_paid(
        self,
        payment_made_service: PaymentMadeService,
        purchase_invoice: Invoice,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        db_session: Session,
    ):
        """
        Test that full payment reduces balance to zero and updates status to PAID.
        
        Requirement 7.4: Reduce outstanding balance by payment amount
        Requirement 7.5: Update Purchase Invoice status to PAID when balance reaches zero
        """
        # Arrange
        full_amount = purchase_invoice.outstanding_amount

        # Act
        payment_made_service.create_payment(
            purchase_invoice_id=purchase_invoice.id,
            amount=full_amount,
            organization_id=organization_id,
            user_id=user_id,
            payment_no="PAY-010",
        )

        # Assert - Refresh invoice to get updated values
        db_session.refresh(purchase_invoice)
        assert purchase_invoice.outstanding_amount == Decimal("0.00")
        assert purchase_invoice.status == InvoiceStatus.PAID

    def test_multiple_partial_payments_eventually_paid(
        self,
        payment_made_service: PaymentMadeService,
        purchase_invoice: Invoice,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        db_session: Session,
    ):
        """
        Test multiple partial payments that eventually pay off the invoice.
        
        Requirement 7.4: Reduce outstanding balance by payment amount
        Requirement 7.5: Update Purchase Invoice status to PAID when balance reaches zero
        """
        # Arrange
        initial_balance = purchase_invoice.outstanding_amount
        first_payment = Decimal("400.00")
        second_payment = Decimal("300.00")
        third_payment = Decimal("300.00")  # Total = 1000.00

        # Act - First payment
        payment_made_service.create_payment(
            purchase_invoice_id=purchase_invoice.id,
            amount=first_payment,
            organization_id=organization_id,
            user_id=user_id,
            payment_no="PAY-011",
        )
        db_session.refresh(purchase_invoice)
        assert purchase_invoice.outstanding_amount == initial_balance - first_payment
        assert purchase_invoice.status == InvoiceStatus.PENDING

        # Act - Second payment
        payment_made_service.create_payment(
            purchase_invoice_id=purchase_invoice.id,
            amount=second_payment,
            organization_id=organization_id,
            user_id=user_id,
            payment_no="PAY-012",
        )
        db_session.refresh(purchase_invoice)
        assert purchase_invoice.outstanding_amount == initial_balance - first_payment - second_payment
        assert purchase_invoice.status == InvoiceStatus.PENDING

        # Act - Third payment (final)
        payment_made_service.create_payment(
            purchase_invoice_id=purchase_invoice.id,
            amount=third_payment,
            organization_id=organization_id,
            user_id=user_id,
            payment_no="PAY-013",
        )
        db_session.refresh(purchase_invoice)
        assert purchase_invoice.outstanding_amount == Decimal("0.00")
        assert purchase_invoice.status == InvoiceStatus.PAID
