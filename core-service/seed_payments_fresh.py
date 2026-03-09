"""Fresh Payment Seed Data - Works with existing unpaid invoices

This script creates payment allocations for existing unpaid invoices.

Usage:
    python seed_payments_fresh.py
"""

import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

# Database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)

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


def create_payments_with_allocations(
    db: Session, org_id: uuid.UUID, admin_user_id: uuid.UUID
):
    """Create payments with allocations for unpaid invoices"""
    from app.models.base import PaymentEntryType, PaymentMode
    from app.schemas.payment_entry import PaymentEntryCreate
    from app.services.allocation_service import AllocationService
    from app.services.payment_entry_service import PaymentEntryService

    print("\n=== Creating Payments with Allocations ===\n")

    payment_service = PaymentEntryService(db)
    allocation_service = AllocationService(db)

    # Get unpaid customer invoices
    customer_invoices = get_unpaid_customer_invoices(db, org_id, 10)
    print(f"Found {len(customer_invoices)} unpaid customer invoices")

    # Get unpaid supplier invoices
    supplier_invoices = get_unpaid_supplier_invoices(db, org_id, 5)
    print(f"Found {len(supplier_invoices)} unpaid supplier invoices\n")

    payment_count = 0
    allocation_count = 0
    payment_modes = [PaymentMode.CASH, PaymentMode.CHECK, PaymentMode.BANK_TRANSFER]

    # Create customer payments with allocations
    for i, invoice in enumerate(customer_invoices[:5]):
        try:
            payment_mode = payment_modes[i % 3]

            payment_data = PaymentEntryCreate(
                payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
                party_id=invoice.customer_id,
                amount=Decimal(str(invoice.balance_due)),
                currency_code="USD",
                payment_date=datetime.now(UTC) - timedelta(days=i),
                payment_mode=payment_mode,
                reference_no=f"PAY-CUST-{7000 + i}"
                if payment_mode != PaymentMode.CASH
                else None,
            )

            payment = payment_service.create_payment_entry(
                data=payment_data, organization_id=org_id, user_id=admin_user_id
            )

            # Allocate to invoice
            allocation_service.create_allocation(
                payment_id=payment.id,
                invoice_id=invoice.id,
                allocated_amount=Decimal(str(invoice.balance_due)),
                organization_id=org_id,
                user_id=admin_user_id,
            )

            # Confirm payment
            confirmed_payment = payment_service.confirm_payment(
                payment_id=payment.id, organization_id=org_id, user_id=admin_user_id
            )

            payment_count += 1
            allocation_count += 1
            print(
                f"  Created payment {confirmed_payment.receipt_number} for invoice {invoice.invoice_no} - ${payment.amount}"
            )

        except Exception as e:
            print(
                f"  Error creating payment for invoice {invoice.invoice_no}: {str(e)}"
            )
            db.rollback()
            continue

    # Create supplier payments with allocations
    for i, invoice in enumerate(supplier_invoices[:3]):
        try:
            payment_data = PaymentEntryCreate(
                payment_type=PaymentEntryType.SUPPLIER_PAYMENT,
                party_id=invoice.supplier_id,
                amount=Decimal(str(invoice.balance_due)),
                currency_code="USD",
                payment_date=datetime.now(UTC) - timedelta(days=10 + i),
                payment_mode=PaymentMode.BANK_TRANSFER,
                reference_no=f"PAY-SUPP-{8000 + i}",
            )

            payment = payment_service.create_payment_entry(
                data=payment_data, organization_id=org_id, user_id=admin_user_id
            )

            # Allocate to invoice
            allocation_service.create_allocation(
                payment_id=payment.id,
                invoice_id=invoice.id,
                allocated_amount=Decimal(str(invoice.balance_due)),
                organization_id=org_id,
                user_id=admin_user_id,
            )

            # Confirm payment
            confirmed_payment = payment_service.confirm_payment(
                payment_id=payment.id, organization_id=org_id, user_id=admin_user_id
            )

            payment_count += 1
            allocation_count += 1
            print(
                f"  Created payment {confirmed_payment.receipt_number} for invoice {invoice.invoice_no} - ${payment.amount}"
            )

        except Exception as e:
            print(
                f"  Error creating payment for invoice {invoice.invoice_no}: {str(e)}"
            )
            db.rollback()
            continue

    print(f"\n  Total payments created: {payment_count}")
    print(f"  Total allocations created: {allocation_count}")
    return payment_count, allocation_count


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

    # Count allocations
    allocation_query = text("""
        SELECT COUNT(*) as count
        FROM payment_references
        WHERE organization_id = :org_id
    """)
    allocation_count = db.execute(allocation_query, {"org_id": org_id}).scalar()

    print(f"\nTotal Payment Allocations: {allocation_count}")

    # Count unpaid invoices remaining
    unpaid_customer_query = text("""
        SELECT COUNT(*) as count
        FROM invoices
        WHERE organization_id = :org_id
        AND invoice_type = 'SALES'
        AND balance_due > 0
    """)
    unpaid_customer_count = db.execute(
        unpaid_customer_query, {"org_id": org_id}
    ).scalar()

    unpaid_supplier_query = text("""
        SELECT COUNT(*) as count
        FROM invoices
        WHERE organization_id = :org_id
        AND invoice_type = 'PURCHASE'
        AND balance_due > 0
    """)
    unpaid_supplier_count = db.execute(
        unpaid_supplier_query, {"org_id": org_id}
    ).scalar()

    print("\nRemaining Unpaid Invoices:")
    print(f"  Customer: {unpaid_customer_count}")
    print(f"  Supplier: {unpaid_supplier_count}")

    print("\n" + "=" * 70)


def main():
    """Main function to run the seeding script"""
    print("=" * 70)
    print("FRESH PAYMENT DATA SEEDING")
    print("=" * 70)

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        print(f"\nUsing Organization ID: {ORG_ID}")
        print(f"Using Admin User ID: {ADMIN_USER_ID}")

        # Create payments with allocations
        payment_count, allocation_count = create_payments_with_allocations(
            db, ORG_ID, ADMIN_USER_ID
        )
        db.commit()

        # Print summary
        print_summary(db, ORG_ID)

        print("\nPayment seeding completed successfully!")

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
