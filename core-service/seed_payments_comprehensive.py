"""Comprehensive Payment Flow Seed Data

This script creates a variety of payment scenarios for testing:
- Draft payments (unallocated)
- Draft payments (with allocations)
- Confirmed payments (fully allocated)
- Confirmed payments (partially allocated)
- Confirmed payments (with unallocated amounts)
- Multiple payment modes (Cash, Check, Bank Transfer)
- Both customer and supplier payments

Usage:
    python seed_payments_comprehensive.py
"""

import os
import sys
import uuid
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db")

# Organization ID
ORG_ID = uuid.UUID("b1f71de1-0a19-424e-9580-1d3f871c5b1f")

# User ID for audit fields
ADMIN_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_unpaid_customer_invoices(db: Session, org_id: uuid.UUID, limit: int = 20):
    """Get unpaid customer invoices"""
    query = text("""
        SELECT id, customer_id, total_amount, balance_due, invoice_no
        FROM invoices
        WHERE organization_id = :org_id
        AND invoice_type = 'SALES'
        AND balance_due > 0
        ORDER BY created_at
        LIMIT :limit
    """)
    return db.execute(query, {"org_id": org_id, "limit": limit}).fetchall()


def get_unpaid_supplier_invoices(db: Session, org_id: uuid.UUID, limit: int = 10):
    """Get unpaid supplier invoices"""
    query = text("""
        SELECT id, supplier_id, total_amount, balance_due, invoice_no
        FROM invoices
        WHERE organization_id = :org_id
        AND invoice_type = 'PURCHASE'
        AND balance_due > 0
        ORDER BY created_at
        LIMIT :limit
    """)
    return db.execute(query, {"org_id": org_id, "limit": limit}).fetchall()


def create_draft_payments(db: Session, org_id: uuid.UUID, admin_user_id: uuid.UUID):
    """Create draft payments (unallocated)"""
    from app.services.payment_entry_service import PaymentEntryService
    from app.models.base import PaymentEntryType, PaymentMode
    from app.schemas.payment_entry import PaymentEntryCreate
    
    print("\n=== Creating Draft Payments (Unallocated) ===\n")
    
    payment_service = PaymentEntryService(db)
    customer_invoices = get_unpaid_customer_invoices(db, org_id, 5)
    
    if not customer_invoices:
        print("  No customer invoices available. Skipping draft payments.")
        return 0
    
    draft_count = 0
    payment_modes = [PaymentMode.CASH, PaymentMode.CHECK, PaymentMode.BANK_TRANSFER]
    
    for i in range(min(5, len(customer_invoices))):
        try:
            invoice = customer_invoices[i]
            payment_mode = payment_modes[i % 3]
            
            payment_data = PaymentEntryCreate(
                payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
                party_id=invoice.customer_id,
                amount=Decimal(str(invoice.balance_due)),
                currency_code="USD",
                payment_date=datetime.now(UTC) - timedelta(days=i),
                payment_mode=payment_mode,
                reference_no=f"DRAFT-{1000 + i}" if payment_mode != PaymentMode.CASH else None
            )
            
            payment = payment_service.create_payment_entry(
                data=payment_data,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            draft_count += 1
            print(f"  Created draft payment {payment.id} - ${payment.amount} ({payment_mode.value})")
            
        except Exception as e:
            print(f"  Error creating draft payment {i+1}: {str(e)}")
            db.rollback()
            continue
    
    print(f"\n  Total draft payments created: {draft_count}")
    return draft_count


def create_draft_payments_with_allocations(db: Session, org_id: uuid.UUID, admin_user_id: uuid.UUID):
    """Create draft payments with allocations"""
    from app.services.payment_entry_service import PaymentEntryService
    from app.services.allocation_service import AllocationService
    from app.models.base import PaymentEntryType, PaymentMode
    from app.schemas.payment_entry import PaymentEntryCreate
    
    print("\n=== Creating Draft Payments (With Allocations) ===\n")
    
    payment_service = PaymentEntryService(db)
    allocation_service = AllocationService(db)
    customer_invoices = get_unpaid_customer_invoices(db, org_id, 10)
    
    if len(customer_invoices) < 5:
        print(f"  Only {len(customer_invoices)} invoices available. Skipping.")
        return 0
    
    allocated_draft_count = 0
    
    for i in range(5, min(10, len(customer_invoices))):
        try:
            invoice = customer_invoices[i]
            payment_mode = PaymentMode.BANK_TRANSFER if i % 2 == 0 else PaymentMode.CHECK
            
            payment_data = PaymentEntryCreate(
                payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
                party_id=invoice.customer_id,
                amount=Decimal(str(invoice.balance_due)),
                currency_code="USD",
                payment_date=datetime.now(UTC) - timedelta(days=i),
                payment_mode=payment_mode,
                reference_no=f"ALLOC-DRAFT-{2000 + i}"
            )
            
            payment = payment_service.create_payment_entry(
                data=payment_data,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            # Allocate to invoice
            allocation_service.create_allocation(
                payment_id=payment.id,
                invoice_id=invoice.id,
                allocated_amount=Decimal(str(invoice.balance_due)),
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            allocated_draft_count += 1
            print(f"  Created draft payment {payment.id} with allocation - ${payment.amount}")
            
        except Exception as e:
            print(f"  Error creating allocated draft payment {i+1}: {str(e)}")
            db.rollback()
            continue
    
    print(f"\n  Total draft payments with allocations: {allocated_draft_count}")
    return allocated_draft_count


def create_confirmed_payments(db: Session, org_id: uuid.UUID, admin_user_id: uuid.UUID):
    """Create confirmed payments (fully allocated)"""
    from app.services.payment_entry_service import PaymentEntryService
    from app.services.allocation_service import AllocationService
    from app.models.base import PaymentEntryType, PaymentMode
    from app.schemas.payment_entry import PaymentEntryCreate
    
    print("\n=== Creating Confirmed Payments (Fully Allocated) ===\n")
    
    payment_service = PaymentEntryService(db)
    allocation_service = AllocationService(db)
    customer_invoices = get_unpaid_customer_invoices(db, org_id, 15)
    
    if len(customer_invoices) < 10:
        print(f"  Only {len(customer_invoices)} invoices available. Skipping.")
        return 0
    
    confirmed_count = 0
    payment_modes = [PaymentMode.CASH, PaymentMode.CHECK, PaymentMode.BANK_TRANSFER]
    
    for i in range(10, min(15, len(customer_invoices))):
        try:
            invoice = customer_invoices[i]
            payment_mode = payment_modes[i % 3]
            
            payment_data = PaymentEntryCreate(
                payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
                party_id=invoice.customer_id,
                amount=Decimal(str(invoice.balance_due)),
                currency_code="USD",
                payment_date=datetime.now(UTC) - timedelta(days=20 + i),
                payment_mode=payment_mode,
                reference_no=f"CONF-{3000 + i}" if payment_mode != PaymentMode.CASH else None
            )
            
            payment = payment_service.create_payment_entry(
                data=payment_data,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            # Allocate to invoice
            allocation_service.create_allocation(
                payment_id=payment.id,
                invoice_id=invoice.id,
                allocated_amount=Decimal(str(invoice.balance_due)),
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            # Confirm payment
            confirmed_payment = payment_service.confirm_payment(
                payment_id=payment.id,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            confirmed_count += 1
            print(f"  Created confirmed payment {confirmed_payment.receipt_number} - ${payment.amount}")
            
        except Exception as e:
            print(f"  Error creating confirmed payment {i+1}: {str(e)}")
            db.rollback()
            continue
    
    print(f"\n  Total confirmed payments created: {confirmed_count}")
    return confirmed_count


def create_confirmed_payments_with_unallocated(db: Session, org_id: uuid.UUID, admin_user_id: uuid.UUID):
    """Create confirmed payments with unallocated amounts"""
    from app.services.payment_entry_service import PaymentEntryService
    from app.services.allocation_service import AllocationService
    from app.models.base import PaymentEntryType, PaymentMode
    from app.schemas.payment_entry import PaymentEntryCreate
    
    print("\n=== Creating Confirmed Payments (With Unallocated Amounts) ===\n")
    
    payment_service = PaymentEntryService(db)
    allocation_service = AllocationService(db)
    customer_invoices = get_unpaid_customer_invoices(db, org_id, 20)
    
    if len(customer_invoices) < 15:
        print(f"  Only {len(customer_invoices)} invoices available. Skipping.")
        return 0
    
    unallocated_count = 0
    
    for i in range(15, min(18, len(customer_invoices))):
        try:
            invoice = customer_invoices[i]
            # Payment amount is more than invoice balance
            payment_amount = Decimal(str(invoice.balance_due)) * Decimal("1.5")
            allocated_amount = Decimal(str(invoice.balance_due))
            
            payment_data = PaymentEntryCreate(
                payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
                party_id=invoice.customer_id,
                amount=payment_amount,
                currency_code="USD",
                payment_date=datetime.now(UTC) - timedelta(days=15 + i),
                payment_mode=PaymentMode.BANK_TRANSFER,
                reference_no=f"UNALLOC-{4000 + i}"
            )
            
            payment = payment_service.create_payment_entry(
                data=payment_data,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            # Allocate only part of the payment
            allocation_service.create_allocation(
                payment_id=payment.id,
                invoice_id=invoice.id,
                allocated_amount=allocated_amount,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            # Confirm payment
            confirmed_payment = payment_service.confirm_payment(
                payment_id=payment.id,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            unallocated_count += 1
            unallocated_amt = payment_amount - allocated_amount
            print(f"  Created payment {confirmed_payment.receipt_number} - ${payment_amount} (${unallocated_amt} unallocated)")
            
        except Exception as e:
            print(f"  Error creating payment with unallocated amount {i+1}: {str(e)}")
            db.rollback()
            continue
    
    print(f"\n  Total payments with unallocated amounts: {unallocated_count}")
    return unallocated_count


def create_supplier_payments(db: Session, org_id: uuid.UUID, admin_user_id: uuid.UUID):
    """Create supplier payments"""
    from app.services.payment_entry_service import PaymentEntryService
    from app.services.allocation_service import AllocationService
    from app.models.base import PaymentEntryType, PaymentMode
    from app.schemas.payment_entry import PaymentEntryCreate
    
    print("\n=== Creating Supplier Payments ===\n")
    
    payment_service = PaymentEntryService(db)
    allocation_service = AllocationService(db)
    supplier_invoices = get_unpaid_supplier_invoices(db, org_id, 10)
    
    if not supplier_invoices:
        print("  No supplier invoices available. Skipping supplier payments.")
        return 0
    
    supplier_payment_count = 0
    
    # Create 3 draft supplier payments
    for i in range(min(3, len(supplier_invoices))):
        try:
            invoice = supplier_invoices[i]
            
            payment_data = PaymentEntryCreate(
                payment_type=PaymentEntryType.SUPPLIER_PAYMENT,
                party_id=invoice.supplier_id,
                amount=Decimal(str(invoice.balance_due)),
                currency_code="USD",
                payment_date=datetime.now(UTC) - timedelta(days=i),
                payment_mode=PaymentMode.BANK_TRANSFER,
                reference_no=f"SUP-DRAFT-{5000 + i}"
            )
            
            payment = payment_service.create_payment_entry(
                data=payment_data,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            supplier_payment_count += 1
            print(f"  Created draft supplier payment {payment.id} - ${payment.amount}")
            
        except Exception as e:
            print(f"  Error creating draft supplier payment {i+1}: {str(e)}")
            db.rollback()
            continue
    
    # Create 5 confirmed supplier payments
    for i in range(3, min(8, len(supplier_invoices))):
        try:
            invoice = supplier_invoices[i]
            
            payment_data = PaymentEntryCreate(
                payment_type=PaymentEntryType.SUPPLIER_PAYMENT,
                party_id=invoice.supplier_id,
                amount=Decimal(str(invoice.balance_due)),
                currency_code="USD",
                payment_date=datetime.now(UTC) - timedelta(days=10 + i),
                payment_mode=PaymentMode.BANK_TRANSFER,
                reference_no=f"SUP-CONF-{6000 + i}"
            )
            
            payment = payment_service.create_payment_entry(
                data=payment_data,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            # Allocate to invoice
            allocation_service.create_allocation(
                payment_id=payment.id,
                invoice_id=invoice.id,
                allocated_amount=Decimal(str(invoice.balance_due)),
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            # Confirm payment
            confirmed_payment = payment_service.confirm_payment(
                payment_id=payment.id,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            supplier_payment_count += 1
            print(f"  Created confirmed supplier payment {confirmed_payment.receipt_number} - ${payment.amount}")
            
        except Exception as e:
            print(f"  Error creating confirmed supplier payment {i+1}: {str(e)}")
            db.rollback()
            continue
    
    print(f"\n  Total supplier payments created: {supplier_payment_count}")
    return supplier_payment_count


def print_summary(db: Session, org_id: uuid.UUID):
    """Print summary of seeded data"""
    print("\n" + "=" * 70)
    print("PAYMENT SEEDING SUMMARY")
    print("=" * 70)
    
    # Count payments by status
    status_query = text("""
        SELECT status, COUNT(*) as count
        FROM payment_entries
        WHERE organization_id = :org_id
        GROUP BY status
    """)
    status_counts = db.execute(status_query, {"org_id": org_id}).fetchall()
    
    print("\nPayments by Status:")
    for row in status_counts:
        print(f"  {row.status}: {row.count}")
    
    # Count payments by type
    type_query = text("""
        SELECT payment_type, COUNT(*) as count
        FROM payment_entries
        WHERE organization_id = :org_id
        GROUP BY payment_type
    """)
    type_counts = db.execute(type_query, {"org_id": org_id}).fetchall()
    
    print("\nPayments by Type:")
    for row in type_counts:
        print(f"  {row.payment_type}: {row.count}")
    
    # Count payments by mode
    mode_query = text("""
        SELECT payment_mode, COUNT(*) as count
        FROM payment_entries
        WHERE organization_id = :org_id
        GROUP BY payment_mode
    """)
    mode_counts = db.execute(mode_query, {"org_id": org_id}).fetchall()
    
    print("\nPayments by Mode:")
    for row in mode_counts:
        print(f"  {row.payment_mode}: {row.count}")
    
    # Count allocations
    allocation_query = text("""
        SELECT COUNT(*) as count
        FROM payment_references
        WHERE organization_id = :org_id
    """)
    allocation_count = db.execute(allocation_query, {"org_id": org_id}).scalar()
    
    print(f"\nTotal Payment Allocations: {allocation_count}")
    
    # Count journal entries
    journal_query = text("""
        SELECT COUNT(*) as count
        FROM journal_entries
        WHERE organization_id = :org_id
        AND reference_type = 'PaymentEntry'
    """)
    journal_count = db.execute(journal_query, {"org_id": org_id}).scalar()
    
    print(f"Total Journal Entries: {journal_count}")
    
    print("\n" + "=" * 70)


def main():
    """Main function to run the seeding script"""
    print("=" * 70)
    print("COMPREHENSIVE PAYMENT FLOW DATA SEEDING")
    print("=" * 70)
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print(f"\nUsing Organization ID: {ORG_ID}")
        print(f"Using Admin User ID: {ADMIN_USER_ID}")
        
        # Create various payment scenarios
        draft_count = create_draft_payments(db, ORG_ID, ADMIN_USER_ID)
        db.commit()
        
        allocated_draft_count = create_draft_payments_with_allocations(db, ORG_ID, ADMIN_USER_ID)
        db.commit()
        
        confirmed_count = create_confirmed_payments(db, ORG_ID, ADMIN_USER_ID)
        db.commit()
        
        unallocated_count = create_confirmed_payments_with_unallocated(db, ORG_ID, ADMIN_USER_ID)
        db.commit()
        
        supplier_count = create_supplier_payments(db, ORG_ID, ADMIN_USER_ID)
        db.commit()
        
        # Print summary
        print_summary(db, ORG_ID)
        
        print("\nPayment Flow seeding completed successfully!")
        
    except Exception as e:
        print(f"\nError during seeding: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
