"""Seed Payment Flow data for testing and demonstration

This script creates comprehensive payment scenarios including:
- Cancelled payments with reversing entries (Task 21.4)

Usage:
    python seed_payments.py
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


def create_cancelled_payments(db: Session, org_id: uuid.UUID, admin_user_id: uuid.UUID):
    """Create cancelled payment scenarios (Task 21.4)"""
    from app.services.payment_entry_service import PaymentEntryService
    from app.services.allocation_service import AllocationService
    from app.models.base import PaymentType, PaymentMode
    
    print("\n=== Creating Cancelled Payment Scenarios (Task 21.4) ===\n")
    
    payment_service = PaymentEntryService(db)
    allocation_service = AllocationService(db)
    
    # Get unpaid customer invoices
    customer_invoices_query = text("""
        SELECT id, customer_id, total_amount, balance_due
        FROM invoices
        WHERE organization_id = :org_id
        AND invoice_type = 'SALES'
        AND balance_due > 0
        ORDER BY created_at
        LIMIT 10
    """)
    customer_invoices = db.execute(customer_invoices_query, {"org_id": org_id}).fetchall()
    
    if len(customer_invoices) < 5:
        print(f"  Warning: Only {len(customer_invoices)} customer invoices available.")
        print(f"  Need to seed invoices first. Skipping cancelled payments.")
        return
    
    # Get unpaid supplier invoices
    supplier_invoices_query = text("""
        SELECT id, supplier_id, total_amount, balance_due
        FROM invoices
        WHERE organization_id = :org_id
        AND invoice_type = 'PURCHASE'
        AND balance_due > 0
        ORDER BY created_at
        LIMIT 5
    """)
    supplier_invoices = db.execute(supplier_invoices_query, {"org_id": org_id}).fetchall()
    
    if len(supplier_invoices) < 2:
        print(f"  Warning: Only {len(supplier_invoices)} supplier invoices available.")
        print(f"  Need to seed invoices first. Skipping cancelled payments.")
        return
    
    cancelled_payments_count = 0
    
    cancellation_reasons = [
        "Duplicate payment - customer paid twice",
        "Customer request - payment made in error",
        "Payment error - wrong amount entered",
        "Bank transfer failed - funds not received",
        "Supplier invoice disputed - payment reversed"
    ]
    
    print("  Creating 3 cancelled customer payments...")
    
    # Create 3 cancelled customer payments
    for i in range(3):
        try:
            invoice = customer_invoices[i]
            payment_amount = invoice.balance_due
            
            from app.schemas.payment_entry import PaymentEntryCreate
            payment_data = PaymentEntryCreate(
                payment_type=PaymentType.CUSTOMER_PAYMENT,
                party_id=invoice.customer_id,
                amount=payment_amount,
                currency_code="USD",
                payment_date=datetime.now(UTC) - timedelta(days=15 - i),
                payment_mode=PaymentMode.BANK_TRANSFER if i % 2 == 0 else PaymentMode.CHECK,
                reference_no=f"CANC-REF-{1000 + i}"
            )
            payment = payment_service.create_payment_entry(
                data=payment_data,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            allocation_service.create_allocation(
                payment_id=payment.id,
                invoice_id=invoice.id,
                allocated_amount=payment_amount,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            confirmed_payment = payment_service.confirm_payment(
                payment_id=payment.id,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            cancelled_payment = payment_service.cancel_payment(
                payment_id=confirmed_payment.id,
                cancellation_reason=cancellation_reasons[i],
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            cancelled_payments_count += 1
            
        except Exception as e:
            print(f"  Error creating cancelled customer payment {i+1}: {str(e)}")
            db.rollback()
            continue
    
    print(f"  Created {cancelled_payments_count} cancelled customer payments")
    
    print("\n  Creating 2 cancelled supplier payments...")
    
    supplier_cancelled_count = 0
    for i in range(2):
        try:
            invoice = supplier_invoices[i]
            payment_amount = invoice.balance_due
            
            from app.schemas.payment_entry import PaymentEntryCreate
            payment_data = PaymentEntryCreate(
                payment_type=PaymentType.SUPPLIER_PAYMENT,
                party_id=invoice.supplier_id,
                amount=payment_amount,
                currency_code="USD",
                payment_date=datetime.now(UTC) - timedelta(days=10 - i),
                payment_mode=PaymentMode.BANK_TRANSFER,
                reference_no=f"SUP-CANC-{2000 + i}"
            )
            payment = payment_service.create_payment_entry(
                data=payment_data,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            allocation_service.create_allocation(
                payment_id=payment.id,
                invoice_id=invoice.id,
                allocated_amount=payment_amount,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            confirmed_payment = payment_service.confirm_payment(
                payment_id=payment.id,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            cancelled_payment = payment_service.cancel_payment(
                payment_id=confirmed_payment.id,
                cancellation_reason=cancellation_reasons[3 + i],
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            supplier_cancelled_count += 1
            
        except Exception as e:
            print(f"  Error creating cancelled supplier payment {i+1}: {str(e)}")
            db.rollback()
            continue
    
    print(f"  Created {supplier_cancelled_count} cancelled supplier payments")
    
    print("\n  Verifying reversing journal entries...")
    
    reversing_entries_query = text("""
        SELECT COUNT(*) as count
        FROM journal_entries je
        WHERE je.organization_id = :org_id
        AND je.reference_type = 'PaymentEntry'
        AND je.remarks LIKE '%Reversal%'
    """)
    reversing_count = db.execute(reversing_entries_query, {"org_id": org_id}).scalar()
    
    print(f"  Found {reversing_count} reversing journal entries")
    
    total_cancelled = cancelled_payments_count + supplier_cancelled_count
    print(f"\n  Task 21.4 Complete:")
    print(f"     - Total cancelled payments: {total_cancelled}")
    print(f"     - Customer payments cancelled: {cancelled_payments_count}")
    print(f"     - Supplier payments cancelled: {supplier_cancelled_count}")
    print(f"     - Reversing journal entries: {reversing_count}")


def main():
    """Main function to run the seeding script"""
    print("=" * 70)
    print("Payment Flow Data Seeding Script - Task 21.4")
    print("=" * 70)
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print(f"\nUsing Organization ID: {ORG_ID}")
        print(f"Using Admin User ID: {ADMIN_USER_ID}")
        
        create_cancelled_payments(db, ORG_ID, ADMIN_USER_ID)
        
        db.commit()
        
        print("\n" + "=" * 70)
        print("Payment Flow seeding completed successfully!")
        print("=" * 70)
        
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
