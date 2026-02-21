"""Tests for PaymentReferenceRepository"""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.payment_reference import PaymentReference
from app.repositories.payment_reference_repository import PaymentReferenceRepository


@pytest.fixture
def payment_reference_repo(db_session):
    """Create a PaymentReferenceRepository instance"""
    return PaymentReferenceRepository(db_session)


@pytest.fixture
def test_organization_id():
    """Test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def test_payment_id():
    """Test payment ID"""
    return uuid.uuid4()


@pytest.fixture
def test_invoice_id():
    """Test invoice ID"""
    return uuid.uuid4()


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return uuid.uuid4()


def test_create_payment_reference(
    payment_reference_repo, test_organization_id, test_payment_id, test_invoice_id, test_user_id
):
    """Test creating a payment reference"""
    data = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "invoice_id": test_invoice_id,
        "allocated_amount": Decimal("100.00"),
        "exchange_rate": Decimal("1.0"),
        "allocated_amount_invoice_currency": Decimal("100.00"),
        "created_by": test_user_id,
    }

    reference = payment_reference_repo.create(data)

    assert reference.id is not None
    assert reference.organization_id == test_organization_id
    assert reference.payment_id == test_payment_id
    assert reference.invoice_id == test_invoice_id
    assert reference.allocated_amount == Decimal("100.00")


def test_create_duplicate_payment_invoice_fails(
    payment_reference_repo, test_organization_id, test_payment_id, test_invoice_id, test_user_id
):
    """Test that creating duplicate payment-invoice reference fails"""
    data = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "invoice_id": test_invoice_id,
        "allocated_amount": Decimal("100.00"),
        "created_by": test_user_id,
    }

    # Create first reference
    payment_reference_repo.create(data)

    # Attempt to create duplicate should fail
    with pytest.raises(IntegrityError):
        payment_reference_repo.create(data)


def test_get_by_payment_id(
    payment_reference_repo, test_organization_id, test_payment_id, test_user_id
):
    """Test getting payment references by payment ID"""
    invoice_id_1 = uuid.uuid4()
    invoice_id_2 = uuid.uuid4()

    # Create two references for the same payment
    data_1 = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "invoice_id": invoice_id_1,
        "allocated_amount": Decimal("50.00"),
        "created_by": test_user_id,
    }
    data_2 = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "invoice_id": invoice_id_2,
        "allocated_amount": Decimal("75.00"),
        "created_by": test_user_id,
    }

    payment_reference_repo.create(data_1)
    payment_reference_repo.create(data_2)

    # Get all references for the payment
    references = payment_reference_repo.get_by_payment_id(test_payment_id, test_organization_id)

    assert len(references) == 2
    assert all(ref.payment_id == test_payment_id for ref in references)


def test_get_by_invoice_id(
    payment_reference_repo, test_organization_id, test_invoice_id, test_user_id
):
    """Test getting payment references by invoice ID"""
    payment_id_1 = uuid.uuid4()
    payment_id_2 = uuid.uuid4()

    # Create two references for the same invoice
    data_1 = {
        "organization_id": test_organization_id,
        "payment_id": payment_id_1,
        "invoice_id": test_invoice_id,
        "allocated_amount": Decimal("30.00"),
        "created_by": test_user_id,
    }
    data_2 = {
        "organization_id": test_organization_id,
        "payment_id": payment_id_2,
        "invoice_id": test_invoice_id,
        "allocated_amount": Decimal("20.00"),
        "created_by": test_user_id,
    }

    payment_reference_repo.create(data_1)
    payment_reference_repo.create(data_2)

    # Get all references for the invoice
    references = payment_reference_repo.get_by_invoice_id(test_invoice_id, test_organization_id)

    assert len(references) == 2
    assert all(ref.invoice_id == test_invoice_id for ref in references)


def test_delete_payment_reference(
    payment_reference_repo, test_organization_id, test_payment_id, test_invoice_id, test_user_id
):
    """Test deleting a payment reference"""
    data = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "invoice_id": test_invoice_id,
        "allocated_amount": Decimal("100.00"),
        "created_by": test_user_id,
    }

    reference = payment_reference_repo.create(data)

    # Delete the reference
    payment_reference_repo.delete(reference)

    # Verify it's deleted
    references = payment_reference_repo.get_by_payment_id(test_payment_id, test_organization_id)
    assert len(references) == 0


def test_get_total_allocated_for_invoice(
    payment_reference_repo, test_organization_id, test_invoice_id, test_user_id
):
    """Test calculating total allocated amount for an invoice"""
    payment_id_1 = uuid.uuid4()
    payment_id_2 = uuid.uuid4()

    # Create two allocations for the same invoice
    data_1 = {
        "organization_id": test_organization_id,
        "payment_id": payment_id_1,
        "invoice_id": test_invoice_id,
        "allocated_amount": Decimal("150.00"),
        "created_by": test_user_id,
    }
    data_2 = {
        "organization_id": test_organization_id,
        "payment_id": payment_id_2,
        "invoice_id": test_invoice_id,
        "allocated_amount": Decimal("75.50"),
        "created_by": test_user_id,
    }

    payment_reference_repo.create(data_1)
    payment_reference_repo.create(data_2)

    # Get total allocated
    total = payment_reference_repo.get_total_allocated_for_invoice(
        test_invoice_id, test_organization_id
    )

    assert total == Decimal("225.50")


def test_get_total_allocated_for_payment(
    payment_reference_repo, test_organization_id, test_payment_id, test_user_id
):
    """Test calculating total allocated amount for a payment"""
    invoice_id_1 = uuid.uuid4()
    invoice_id_2 = uuid.uuid4()
    invoice_id_3 = uuid.uuid4()

    # Create three allocations for the same payment
    data_1 = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "invoice_id": invoice_id_1,
        "allocated_amount": Decimal("50.00"),
        "created_by": test_user_id,
    }
    data_2 = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "invoice_id": invoice_id_2,
        "allocated_amount": Decimal("30.00"),
        "created_by": test_user_id,
    }
    data_3 = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "invoice_id": invoice_id_3,
        "allocated_amount": Decimal("20.25"),
        "created_by": test_user_id,
    }

    payment_reference_repo.create(data_1)
    payment_reference_repo.create(data_2)
    payment_reference_repo.create(data_3)

    # Get total allocated
    total = payment_reference_repo.get_total_allocated_for_payment(
        test_payment_id, test_organization_id
    )

    assert total == Decimal("100.25")


def test_get_total_allocated_for_invoice_no_allocations(
    payment_reference_repo, test_organization_id
):
    """Test that total allocated returns 0.00 when no allocations exist"""
    invoice_id = uuid.uuid4()

    total = payment_reference_repo.get_total_allocated_for_invoice(
        invoice_id, test_organization_id
    )

    assert total == Decimal("0.00")


def test_get_total_allocated_for_payment_no_allocations(
    payment_reference_repo, test_organization_id
):
    """Test that total allocated returns 0.00 when no allocations exist"""
    payment_id = uuid.uuid4()

    total = payment_reference_repo.get_total_allocated_for_payment(
        payment_id, test_organization_id
    )

    assert total == Decimal("0.00")


def test_multi_tenancy_isolation(
    payment_reference_repo, test_payment_id, test_invoice_id, test_user_id
):
    """Test that organization_id filtering works correctly"""
    org_1 = uuid.uuid4()
    org_2 = uuid.uuid4()

    # Create reference for org_1
    data_1 = {
        "organization_id": org_1,
        "payment_id": test_payment_id,
        "invoice_id": test_invoice_id,
        "allocated_amount": Decimal("100.00"),
        "created_by": test_user_id,
    }
    payment_reference_repo.create(data_1)

    # Query with org_2 should return empty
    references = payment_reference_repo.get_by_payment_id(test_payment_id, org_2)
    assert len(references) == 0

    # Query with org_1 should return the reference
    references = payment_reference_repo.get_by_payment_id(test_payment_id, org_1)
    assert len(references) == 1
