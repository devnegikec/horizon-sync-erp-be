"""Tests for AllocationService.create_bulk_allocations() method"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.base import PaymentEntryStatus, PaymentEntryType, PaymentMode
from app.models.invoice import Invoice
from app.models.payment_entry import PaymentEntry
from app.services.allocation_service import AllocationService


@pytest.fixture
def test_organization_id():
    """Test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return uuid.uuid4()


def test_create_bulk_allocations_success(
    db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID
):
    """Test successful bulk allocation to multiple invoices"""
    # Create a payment entry with enough amount for multiple allocations
    party_id = uuid.uuid4()
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=party_id,
        amount=Decimal("2000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(payment)

    # Create multiple invoices
    invoice1 = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-001",
        invoice_type="sales",
        party_id=party_id,
        party_type="customer",
        grand_total=Decimal("500.00"),
        outstanding_amount=Decimal("500.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    invoice2 = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-002",
        invoice_type="sales",
        party_id=party_id,
        party_type="customer",
        grand_total=Decimal("800.00"),
        outstanding_amount=Decimal("800.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    invoice3 = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-003",
        invoice_type="sales",
        party_id=party_id,
        party_type="customer",
        grand_total=Decimal("300.00"),
        outstanding_amount=Decimal("300.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add_all([invoice1, invoice2, invoice3])
    db_session.commit()

    # Create bulk allocations
    service = AllocationService(db_session)
    allocations = [
        {"invoice_id": invoice1.id, "allocated_amount": Decimal("500.00")},
        {"invoice_id": invoice2.id, "allocated_amount": Decimal("800.00")},
        {"invoice_id": invoice3.id, "allocated_amount": Decimal("300.00")},
    ]

    references = service.create_bulk_allocations(
        payment_id=payment.id,
        allocations=allocations,
        organization_id=test_organization_id,
        user_id=test_user_id,
    )

    # Verify all allocations were created
    assert len(references) == 3
    assert references[0].invoice_id == invoice1.id
    assert references[0].allocated_amount == Decimal("500.00")
    assert references[1].invoice_id == invoice2.id
    assert references[1].allocated_amount == Decimal("800.00")
    assert references[2].invoice_id == invoice3.id
    assert references[2].allocated_amount == Decimal("300.00")


def test_create_bulk_allocations_exceeds_payment_amount(
    db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID
):
    """Test that bulk allocation fails when total exceeds payment amount"""
    party_id = uuid.uuid4()
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=party_id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(payment)

    # Create invoices
    invoice1 = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-004",
        invoice_type="sales",
        party_id=party_id,
        party_type="customer",
        grand_total=Decimal("600.00"),
        outstanding_amount=Decimal("600.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    invoice2 = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-005",
        invoice_type="sales",
        party_id=party_id,
        party_type="customer",
        grand_total=Decimal("700.00"),
        outstanding_amount=Decimal("700.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add_all([invoice1, invoice2])
    db_session.commit()

    # Try to allocate more than payment amount
    service = AllocationService(db_session)
    allocations = [
        {"invoice_id": invoice1.id, "allocated_amount": Decimal("600.00")},
        {
            "invoice_id": invoice2.id,
            "allocated_amount": Decimal("700.00"),
        },  # Total = 1300 > 1000
    ]

    with pytest.raises(ValidationError, match="exceeds payment unallocated amount"):
        service.create_bulk_allocations(
            payment_id=payment.id,
            allocations=allocations,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )


def test_create_bulk_allocations_different_parties(
    db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID
):
    """Test that bulk allocation fails when invoices belong to different parties"""
    party_id1 = uuid.uuid4()
    party_id2 = uuid.uuid4()

    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=party_id1,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(payment)

    # Create invoices with different parties
    invoice1 = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-006",
        invoice_type="sales",
        party_id=party_id1,  # Same party as payment
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
        invoice_no="INV-007",
        invoice_type="sales",
        party_id=party_id2,  # Different party
        party_type="customer",
        grand_total=Decimal("300.00"),
        outstanding_amount=Decimal("300.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add_all([invoice1, invoice2])
    db_session.commit()

    # Try to allocate to invoices with different parties
    service = AllocationService(db_session)
    allocations = [
        {"invoice_id": invoice1.id, "allocated_amount": Decimal("400.00")},
        {"invoice_id": invoice2.id, "allocated_amount": Decimal("300.00")},
    ]

    with pytest.raises(ValidationError, match="does not match payment party"):
        service.create_bulk_allocations(
            payment_id=payment.id,
            allocations=allocations,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )


def test_create_bulk_allocations_different_organizations(
    db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID
):
    """Test that bulk allocation fails when invoices belong to different organizations"""
    party_id = uuid.uuid4()
    other_org_id = uuid.uuid4()

    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=party_id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(payment)

    # Create invoices with different organizations
    invoice1 = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-008",
        invoice_type="sales",
        party_id=party_id,
        party_type="customer",
        grand_total=Decimal("400.00"),
        outstanding_amount=Decimal("400.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    invoice2 = Invoice(
        id=uuid.uuid4(),
        organization_id=other_org_id,  # Different organization
        invoice_no="INV-009",
        invoice_type="sales",
        party_id=party_id,
        party_type="customer",
        grand_total=Decimal("300.00"),
        outstanding_amount=Decimal("300.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add_all([invoice1, invoice2])
    db_session.commit()

    # Try to allocate to invoices with different organizations
    service = AllocationService(db_session)
    allocations = [
        {"invoice_id": invoice1.id, "allocated_amount": Decimal("400.00")},
        {"invoice_id": invoice2.id, "allocated_amount": Decimal("300.00")},
    ]

    # The invoice from different organization won't be found by get_by_id
    # because it filters by organization_id
    with pytest.raises(
        ValidationError, match="not found or does not belong to organization"
    ):
        service.create_bulk_allocations(
            payment_id=payment.id,
            allocations=allocations,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )


def test_create_bulk_allocations_exceeds_invoice_balance(
    db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID
):
    """Test that bulk allocation fails when any allocation exceeds invoice outstanding balance"""
    party_id = uuid.uuid4()
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=party_id,
        amount=Decimal("2000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(payment)

    # Create invoice with limited outstanding balance
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-010",
        invoice_type="sales",
        party_id=party_id,
        party_type="customer",
        grand_total=Decimal("500.00"),
        outstanding_amount=Decimal("500.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(invoice)
    db_session.commit()

    # Try to allocate more than invoice outstanding balance
    service = AllocationService(db_session)
    allocations = [
        {
            "invoice_id": invoice.id,
            "allocated_amount": Decimal("800.00"),
        },  # Exceeds 500
    ]

    with pytest.raises(ValidationError, match="exceeds invoice outstanding balance"):
        service.create_bulk_allocations(
            payment_id=payment.id,
            allocations=allocations,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )


def test_create_bulk_allocations_payment_not_draft(
    db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID
):
    """Test that bulk allocation fails when payment is not in Draft status"""
    party_id = uuid.uuid4()
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=party_id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.CONFIRMED,  # Not Draft
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(payment)

    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-011",
        invoice_type="sales",
        party_id=party_id,
        party_type="customer",
        grand_total=Decimal("500.00"),
        outstanding_amount=Decimal("500.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(invoice)
    db_session.commit()

    # Try to create bulk allocations
    service = AllocationService(db_session)
    allocations = [
        {"invoice_id": invoice.id, "allocated_amount": Decimal("500.00")},
    ]

    with pytest.raises(ValidationError, match="Payment must be in Draft status"):
        service.create_bulk_allocations(
            payment_id=payment.id,
            allocations=allocations,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )


def test_create_bulk_allocations_empty_list(
    db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID
):
    """Test that bulk allocation fails with empty allocations list"""
    party_id = uuid.uuid4()
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=party_id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(payment)
    db_session.commit()

    # Try to create bulk allocations with empty list
    service = AllocationService(db_session)

    with pytest.raises(ValidationError, match="At least one allocation is required"):
        service.create_bulk_allocations(
            payment_id=payment.id,
            allocations=[],
            organization_id=test_organization_id,
            user_id=test_user_id,
        )


def test_create_bulk_allocations_partial_amount(
    db_session: Session, test_organization_id: uuid.UUID, test_user_id: uuid.UUID
):
    """Test successful bulk allocation with partial payment amount (leaving unallocated amount)"""
    party_id = uuid.uuid4()
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=party_id,
        amount=Decimal("2000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(payment)

    # Create invoices
    invoice1 = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-012",
        invoice_type="sales",
        party_id=party_id,
        party_type="customer",
        grand_total=Decimal("500.00"),
        outstanding_amount=Decimal("500.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    invoice2 = Invoice(
        id=uuid.uuid4(),
        organization_id=test_organization_id,
        invoice_no="INV-013",
        invoice_type="sales",
        party_id=party_id,
        party_type="customer",
        grand_total=Decimal("300.00"),
        outstanding_amount=Decimal("300.00"),
        currency="USD",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add_all([invoice1, invoice2])
    db_session.commit()

    # Allocate only partial amount (800 out of 2000)
    service = AllocationService(db_session)
    allocations = [
        {"invoice_id": invoice1.id, "allocated_amount": Decimal("500.00")},
        {"invoice_id": invoice2.id, "allocated_amount": Decimal("300.00")},
    ]

    references = service.create_bulk_allocations(
        payment_id=payment.id,
        allocations=allocations,
        organization_id=test_organization_id,
        user_id=test_user_id,
    )

    # Verify allocations were created
    assert len(references) == 2
    # Payment should still have unallocated amount (2000 - 800 = 1200)
