"""Tests for ReconciliationReportService"""

import pytest
from datetime import datetime, UTC
from decimal import Decimal
from uuid import uuid4

from app.services.reconciliation_report_service import ReconciliationReportService
from app.models.payment_entry import PaymentEntry
from app.models.payment_reference import PaymentReference
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.base import (
    PaymentEntryType,
    PaymentMode,
    PaymentEntryStatus,
    PaymentSource,
)


@pytest.fixture
def test_organization():
    """Create a test organization ID"""
    return type('Organization', (), {'id': uuid4()})()


@pytest.fixture
def test_customer(db_session, test_organization):
    """Create a test customer"""
    customer = Customer(
        id=uuid4(),
        organization_id=test_organization.id,
        customer_name="Test Customer",
        customer_code="CUST001",
        email="test@example.com",
    )
    db_session.add(customer)
    db_session.commit()
    return customer


@pytest.fixture
def test_user():
    """Create a test user ID"""
    return type('User', (), {'id': uuid4()})()


@pytest.fixture
def test_invoice(db_session, test_organization, test_customer):
    """Create a test invoice"""
    invoice = Invoice(
        id=uuid4(),
        organization_id=test_organization.id,
        customer_id=test_customer.id,
        invoice_number="INV-2024-001",
        invoice_date=datetime(2024, 6, 1, tzinfo=UTC),
        total_amount=Decimal("1000.00"),
        status="Unpaid",
    )
    db_session.add(invoice)
    db_session.commit()
    return invoice


def test_generate_report_with_no_payments(db_session, test_organization):
    """Test generating report when no payments exist"""
    service = ReconciliationReportService(db_session)
    
    report = service.generate_report(
        organization_id=test_organization.id,
        date_from=datetime(2024, 1, 1, tzinfo=UTC),
        date_to=datetime(2024, 12, 31, tzinfo=UTC),
    )
    
    assert report["summary"]["total_payments_received"] == "0.00"
    assert report["summary"]["total_allocated"] == "0.00"
    assert report["summary"]["total_unallocated"] == "0.00"
    assert report["summary"]["payment_count"] == 0
    assert len(report["payments"]) == 0


def test_generate_report_with_payments(db_session, test_organization, test_customer, test_user):
    """Test generating report with payments and allocations"""
    service = ReconciliationReportService(db_session)
    
    # Create test payment entries
    payment1 = PaymentEntry(
        organization_id=test_organization.id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=test_customer.id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime(2024, 6, 15, tzinfo=UTC),
        payment_mode=PaymentMode.BANK_TRANSFER,
        reference_no="UTR123456",
        status=PaymentEntryStatus.CONFIRMED,
        source=PaymentSource.MANUAL,
        receipt_number="RCP-2024-001",
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(payment1)
    
    payment2 = PaymentEntry(
        organization_id=test_organization.id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=test_customer.id,
        amount=Decimal("500.00"),
        currency_code="USD",
        payment_date=datetime(2024, 6, 20, tzinfo=UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        source=PaymentSource.MANUAL,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(payment2)
    db_session.commit()
    
    # Generate report
    report = service.generate_report(
        organization_id=test_organization.id,
        date_from=datetime(2024, 6, 1, tzinfo=UTC),
        date_to=datetime(2024, 6, 30, tzinfo=UTC),
    )
    
    # Verify summary
    assert report["summary"]["total_payments_received"] == "1500.00"
    assert report["summary"]["payment_count"] == 2
    
    # Verify payments by status
    assert "Confirmed" in report["payments_by_status"]
    assert report["payments_by_status"]["Confirmed"]["count"] == 1
    assert report["payments_by_status"]["Confirmed"]["total_amount"] == "1000.00"
    
    assert "Draft" in report["payments_by_status"]
    assert report["payments_by_status"]["Draft"]["count"] == 1
    assert report["payments_by_status"]["Draft"]["total_amount"] == "500.00"
    
    # Verify payments by mode
    assert "Bank_Transfer" in report["payments_by_mode"]
    assert report["payments_by_mode"]["Bank_Transfer"]["count"] == 1
    
    assert "Cash" in report["payments_by_mode"]
    assert report["payments_by_mode"]["Cash"]["count"] == 1
    
    # Verify payments list
    assert len(report["payments"]) == 2


def test_generate_report_with_allocations(
    db_session, test_organization, test_customer, test_user, test_invoice
):
    """Test generating report with payment allocations"""
    service = ReconciliationReportService(db_session)
    
    # Create payment with allocation
    payment = PaymentEntry(
        organization_id=test_organization.id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=test_customer.id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime(2024, 6, 15, tzinfo=UTC),
        payment_mode=PaymentMode.BANK_TRANSFER,
        reference_no="UTR123456",
        status=PaymentEntryStatus.CONFIRMED,
        source=PaymentSource.MANUAL,
        receipt_number="RCP-2024-001",
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(payment)
    db_session.commit()
    
    # Create payment reference (allocation)
    payment_ref = PaymentReference(
        organization_id=test_organization.id,
        payment_id=payment.id,
        invoice_id=test_invoice.id,
        allocated_amount=Decimal("600.00"),
        exchange_rate=Decimal("1.0"),
        allocated_amount_invoice_currency=Decimal("600.00"),
        created_by=test_user.id,
    )
    db_session.add(payment_ref)
    db_session.commit()
    
    # Generate report
    report = service.generate_report(
        organization_id=test_organization.id,
        date_from=datetime(2024, 6, 1, tzinfo=UTC),
        date_to=datetime(2024, 6, 30, tzinfo=UTC),
    )
    
    # Verify summary
    assert report["summary"]["total_payments_received"] == "1000.00"
    assert report["summary"]["total_allocated"] == "600.00"
    assert report["summary"]["total_unallocated"] == "400.00"
    assert report["summary"]["unallocated_payment_count"] == 1
    
    # Verify payment details
    assert len(report["payments"]) == 1
    payment_data = report["payments"][0]
    assert payment_data["unallocated_amount"] == "400.00"
    assert payment_data["allocation_count"] == 1
    assert len(payment_data["allocated_invoices"]) == 1
    
    # Verify allocated invoice details
    allocated_invoice = payment_data["allocated_invoices"][0]
    assert allocated_invoice["invoice_id"] == str(test_invoice.id)
    assert allocated_invoice["allocated_amount"] == "600.00"
    
    # Verify unallocated payments list
    assert len(report["unallocated_payments"]) == 1


def test_generate_report_with_filters(
    db_session, test_organization, test_customer, test_user
):
    """Test generating report with various filters"""
    service = ReconciliationReportService(db_session)
    
    # Create payments with different modes and statuses
    payment1 = PaymentEntry(
        organization_id=test_organization.id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=test_customer.id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime(2024, 6, 15, tzinfo=UTC),
        payment_mode=PaymentMode.BANK_TRANSFER,
        reference_no="UTR123456",
        status=PaymentEntryStatus.CONFIRMED,
        source=PaymentSource.MANUAL,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(payment1)
    
    payment2 = PaymentEntry(
        organization_id=test_organization.id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=test_customer.id,
        amount=Decimal("500.00"),
        currency_code="USD",
        payment_date=datetime(2024, 6, 20, tzinfo=UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        source=PaymentSource.MANUAL,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(payment2)
    db_session.commit()
    
    # Test filter by status
    report = service.generate_report(
        organization_id=test_organization.id,
        status="Confirmed",
    )
    assert report["summary"]["payment_count"] == 1
    assert report["summary"]["total_payments_received"] == "1000.00"
    
    # Test filter by payment_mode
    report = service.generate_report(
        organization_id=test_organization.id,
        payment_mode="Cash",
    )
    assert report["summary"]["payment_count"] == 1
    assert report["summary"]["total_payments_received"] == "500.00"
    
    # Test filter by party_id
    report = service.generate_report(
        organization_id=test_organization.id,
        party_id=test_customer.id,
    )
    assert report["summary"]["payment_count"] == 2


def test_generate_report_multi_tenancy_isolation(
    db_session, test_organization, test_customer, test_user
):
    """Test that report only includes payments from specified organization"""
    service = ReconciliationReportService(db_session)
    
    # Create payment for test organization
    payment1 = PaymentEntry(
        organization_id=test_organization.id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=test_customer.id,
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime(2024, 6, 15, tzinfo=UTC),
        payment_mode=PaymentMode.BANK_TRANSFER,
        reference_no="UTR123456",
        status=PaymentEntryStatus.CONFIRMED,
        source=PaymentSource.MANUAL,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(payment1)
    
    # Create payment for different organization
    other_org_id = uuid4()
    payment2 = PaymentEntry(
        organization_id=other_org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=test_customer.id,
        amount=Decimal("500.00"),
        currency_code="USD",
        payment_date=datetime(2024, 6, 20, tzinfo=UTC),
        payment_mode=PaymentMode.CASH,
        status=PaymentEntryStatus.DRAFT,
        source=PaymentSource.MANUAL,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(payment2)
    db_session.commit()
    
    # Generate report for test organization
    report = service.generate_report(
        organization_id=test_organization.id,
    )
    
    # Should only include payment from test organization
    assert report["summary"]["payment_count"] == 1
    assert report["summary"]["total_payments_received"] == "1000.00"
