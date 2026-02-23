"""Tests for payment entry caching functionality"""

import pytest
from decimal import Decimal
from datetime import datetime, UTC
from uuid import uuid4

from app.core.cache import (
    cache,
    get_payment_cache_key,
    get_payment_list_cache_key,
    get_unpaid_invoices_cache_key,
    invalidate_payment_cache,
    invalidate_invoice_cache,
)
from app.models.base import PaymentEntryStatus, PaymentMode, PaymentEntryType
from app.models.payment_entry import PaymentEntry
from app.services.payment_entry_service import PaymentEntryService
from app.services.allocation_service import AllocationService
from app.schemas.payment_entry import PaymentEntryCreate


class TestPaymentCaching:
    """Test payment caching functionality"""

    def test_cache_invalidation_on_payment_create(
        self,
        db_session,
        test_organization_id,
        test_user_id,
        test_customer_id,
    ):
        """Test that creating a payment invalidates the payment list cache"""
        # Pre-populate cache with a fake payment list
        cache_key = get_payment_list_cache_key(
            organization_id=test_organization_id,
            status=None,
            payment_mode=None,
            party_id=None,
            page=1,
            page_size=50,
        )
        cache.set(cache_key, {"payments": [], "total": 0}, ttl=300)
        
        # Verify cache is populated
        assert cache.get(cache_key) is not None
        
        # Create a payment
        service = PaymentEntryService(db_session)
        payment_data = PaymentEntryCreate(
            payment_type="Customer_Payment",
            party_id=test_customer_id,
            amount=Decimal("1000.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            payment_mode="Cash",
            reference_no=None,
        )
        
        payment = service.create_payment_entry(
            data=payment_data,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        
        # Verify cache was invalidated (should be None now)
        assert cache.get(cache_key) is None

    def test_cache_invalidation_on_payment_update(
        self,
        db_session,
        test_organization_id,
        test_user_id,
        test_customer_id,
    ):
        """Test that updating a payment invalidates the cache"""
        from app.schemas.payment_entry import PaymentEntryUpdate
        
        # Create a payment first
        service = PaymentEntryService(db_session)
        payment_data = PaymentEntryCreate(
            payment_type="Customer_Payment",
            party_id=test_customer_id,
            amount=Decimal("1000.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            payment_mode="Cash",
            reference_no=None,
        )
        
        payment = service.create_payment_entry(
            data=payment_data,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        
        # Pre-populate cache
        cache_key = get_payment_list_cache_key(
            organization_id=test_organization_id,
            status=None,
            payment_mode=None,
            party_id=None,
            page=1,
            page_size=50,
        )
        cache.set(cache_key, {"payments": [], "total": 0}, ttl=300)
        assert cache.get(cache_key) is not None
        
        # Update the payment
        update_data = PaymentEntryUpdate(amount=Decimal("1500.00"))
        service.update_payment_entry(
            payment_id=payment.id,
            data=update_data,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        
        # Verify cache was invalidated
        assert cache.get(cache_key) is None

    def test_cache_invalidation_on_payment_confirm(
        self,
        db_session,
        test_organization_id,
        test_user_id,
        test_customer_id,
    ):
        """Test that confirming a payment invalidates the cache"""
        # Create a payment with allocation
        service = PaymentEntryService(db_session)
        payment_data = PaymentEntryCreate(
            payment_type="Customer_Payment",
            party_id=test_customer_id,
            amount=Decimal("1000.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            payment_mode="Cash",
            reference_no=None,
        )
        
        payment = service.create_payment_entry(
            data=payment_data,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        
        # Create an invoice for allocation
        from app.models.invoice import Invoice
        invoice = Invoice(
            organization_id=test_organization_id,
            party_id=test_customer_id,
            invoice_type="SALES",
            invoice_number="INV-001",
            posting_date=datetime.now(UTC),
            due_date=datetime.now(UTC),
            grand_total=Decimal("1000.00"),
            outstanding_balance=Decimal("1000.00"),
            status="Unpaid",
        )
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)
        
        # Create allocation
        allocation_service = AllocationService(db_session)
        allocation_service.create_allocation(
            payment_id=payment.id,
            invoice_id=invoice.id,
            allocated_amount=Decimal("1000.00"),
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        
        # Pre-populate cache
        cache_key = get_payment_list_cache_key(
            organization_id=test_organization_id,
            status=None,
            payment_mode=None,
            party_id=None,
            page=1,
            page_size=50,
        )
        cache.set(cache_key, {"payments": [], "total": 0}, ttl=300)
        assert cache.get(cache_key) is not None
        
        # Confirm the payment (requires default accounts to be configured)
        # This test will skip confirmation if default accounts are not set up
        try:
            service.confirm_payment(
                payment_id=payment.id,
                organization_id=test_organization_id,
                user_id=test_user_id,
            )
            
            # Verify cache was invalidated
            assert cache.get(cache_key) is None
        except Exception as e:
            # If default accounts are not configured, skip this test
            if "default account" in str(e).lower():
                pytest.skip("Default accounts not configured for testing")
            else:
                raise

    def test_cache_invalidation_on_allocation_create(
        self,
        db_session,
        test_organization_id,
        test_user_id,
        test_customer_id,
    ):
        """Test that creating an allocation invalidates both payment and invoice caches"""
        # Create a payment
        service = PaymentEntryService(db_session)
        payment_data = PaymentEntryCreate(
            payment_type="Customer_Payment",
            party_id=test_customer_id,
            amount=Decimal("1000.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            payment_mode="Cash",
            reference_no=None,
        )
        
        payment = service.create_payment_entry(
            data=payment_data,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        
        # Create an invoice
        from app.models.invoice import Invoice
        invoice = Invoice(
            organization_id=test_organization_id,
            party_id=test_customer_id,
            invoice_type="SALES",
            invoice_number="INV-002",
            posting_date=datetime.now(UTC),
            due_date=datetime.now(UTC),
            grand_total=Decimal("1000.00"),
            outstanding_balance=Decimal("1000.00"),
            status="Unpaid",
        )
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)
        
        # Pre-populate caches
        payment_cache_key = get_payment_list_cache_key(
            organization_id=test_organization_id,
            status=None,
            payment_mode=None,
            party_id=None,
            page=1,
            page_size=50,
        )
        invoice_cache_key = get_unpaid_invoices_cache_key(
            party_id=test_customer_id,
            organization_id=test_organization_id,
        )
        
        cache.set(payment_cache_key, {"payments": [], "total": 0}, ttl=300)
        cache.set(invoice_cache_key, {"invoices": []}, ttl=300)
        
        assert cache.get(payment_cache_key) is not None
        assert cache.get(invoice_cache_key) is not None
        
        # Create allocation
        allocation_service = AllocationService(db_session)
        allocation_service.create_allocation(
            payment_id=payment.id,
            invoice_id=invoice.id,
            allocated_amount=Decimal("1000.00"),
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        
        # Verify both caches were invalidated
        assert cache.get(payment_cache_key) is None
        assert cache.get(invoice_cache_key) is None

    def test_cache_invalidation_on_allocation_remove(
        self,
        db_session,
        test_organization_id,
        test_user_id,
        test_customer_id,
    ):
        """Test that removing an allocation invalidates both payment and invoice caches"""
        # Create a payment
        service = PaymentEntryService(db_session)
        payment_data = PaymentEntryCreate(
            payment_type="Customer_Payment",
            party_id=test_customer_id,
            amount=Decimal("1000.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            payment_mode="Cash",
            reference_no=None,
        )
        
        payment = service.create_payment_entry(
            data=payment_data,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        
        # Create an invoice
        from app.models.invoice import Invoice
        invoice = Invoice(
            organization_id=test_organization_id,
            party_id=test_customer_id,
            invoice_type="SALES",
            invoice_number="INV-003",
            posting_date=datetime.now(UTC),
            due_date=datetime.now(UTC),
            grand_total=Decimal("1000.00"),
            outstanding_balance=Decimal("1000.00"),
            status="Unpaid",
        )
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)
        
        # Create allocation
        allocation_service = AllocationService(db_session)
        allocation = allocation_service.create_allocation(
            payment_id=payment.id,
            invoice_id=invoice.id,
            allocated_amount=Decimal("1000.00"),
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        
        # Pre-populate caches
        payment_cache_key = get_payment_list_cache_key(
            organization_id=test_organization_id,
            status=None,
            payment_mode=None,
            party_id=None,
            page=1,
            page_size=50,
        )
        invoice_cache_key = get_unpaid_invoices_cache_key(
            party_id=test_customer_id,
            organization_id=test_organization_id,
        )
        
        cache.set(payment_cache_key, {"payments": [], "total": 0}, ttl=300)
        cache.set(invoice_cache_key, {"invoices": []}, ttl=300)
        
        assert cache.get(payment_cache_key) is not None
        assert cache.get(invoice_cache_key) is not None
        
        # Remove allocation
        allocation_service.remove_allocation(
            allocation_id=allocation.id,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        
        # Verify both caches were invalidated
        assert cache.get(payment_cache_key) is None
        assert cache.get(invoice_cache_key) is None
