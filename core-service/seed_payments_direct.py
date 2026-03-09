"""Seed cancelled payments directly - Task 21.4

This script creates cancelled payment scenarios by directly inserting into the database,
bypassing the service layer to avoid model/schema mismatches.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)
ORG_ID = uuid.UUID("b1f71de1-0a19-424e-9580-1d3f871c5b1f")
ADMIN_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def main():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        print("=" * 70)
        print("Creating Cancelled Payment Scenarios - Task 21.4")
        print("=" * 70)

        # Get customer invoices
        customer_invoices = db.execute(
            text("""
            SELECT id, customer_id, total_amount, balance_due
            FROM invoices
            WHERE organization_id = :org_id
            AND invoice_type = 'SALES'
            AND balance_due > 0
            ORDER BY created_at
            LIMIT 3
        """),
            {"org_id": ORG_ID},
        ).fetchall()

        if len(customer_invoices) < 3:
            print(
                f"\n❌ Need at least 3 customer invoices, found {len(customer_invoices)}"
            )
            return

        # Get supplier invoices
        supplier_invoices = db.execute(
            text("""
            SELECT id, supplier_id, total_amount, balance_due
            FROM invoices
            WHERE organization_id = :org_id
            AND invoice_type = 'PURCHASE'
            AND balance_due > 0
            ORDER BY created_at
            LIMIT 2
        """),
            {"org_id": ORG_ID},
        ).fetchall()

        if len(supplier_invoices) < 2:
            print(
                f"\n❌ Need at least 2 supplier invoices, found {len(supplier_invoices)}"
            )
            return

        cancellation_reasons = [
            "Duplicate payment - customer paid twice",
            "Customer request - payment made in error",
            "Payment error - wrong amount entered",
            "Bank transfer failed - funds not received",
            "Supplier invoice disputed - payment reversed",
        ]

        print("\n📝 Creating 3 cancelled customer payments...")

        for i in range(3):
            invoice = customer_invoices[i]
            payment_id = uuid.uuid4()
            payment_amount = invoice.balance_due
            payment_date = datetime.now(UTC) - timedelta(days=15 - i)
            payment_mode = "Bank_Transfer" if i % 2 == 0 else "Check"

            # Create payment entry (Draft)
            db.execute(
                text("""
                INSERT INTO payment_entries (
                    id, organization_id, payment_type, party_id, amount, currency_code,
                    payment_date, payment_mode, reference_no, status, source,
                    created_by, updated_by, created_at, updated_at
                ) VALUES (
                    :id, :org_id, 'Customer_Payment', :party_id, :amount, 'USD',
                    :payment_date, :payment_mode, :reference_no, 'Draft', 'Manual',
                    :user_id, :user_id, :created_at, :updated_at
                )
            """),
                {
                    "id": payment_id,
                    "org_id": ORG_ID,
                    "party_id": invoice.customer_id,
                    "amount": payment_amount,
                    "payment_date": payment_date,
                    "payment_mode": payment_mode,
                    "reference_no": f"CANC-REF-{1000 + i}",
                    "user_id": ADMIN_USER_ID,
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
            )

            # Create allocation
            db.execute(
                text("""
                INSERT INTO payment_references (
                    id, organization_id, payment_id, invoice_id, allocated_amount,
                    exchange_rate, allocated_amount_invoice_currency, created_by, created_at
                ) VALUES (
                    :id, :org_id, :payment_id, :invoice_id, :allocated_amount,
                    1.0, :allocated_amount, :user_id, :created_at
                )
            """),
                {
                    "id": uuid.uuid4(),
                    "org_id": ORG_ID,
                    "payment_id": payment_id,
                    "invoice_id": invoice.id,
                    "allocated_amount": payment_amount,
                    "user_id": ADMIN_USER_ID,
                    "created_at": datetime.now(UTC),
                },
            )

            # Confirm payment (update status and add receipt number)
            receipt_number = f"RCP-2026-{1000 + i}"
            db.execute(
                text("""
                UPDATE payment_entries
                SET status = 'Confirmed', receipt_number = :receipt_number, updated_at = :updated_at
                WHERE id = :payment_id
            """),
                {
                    "payment_id": payment_id,
                    "receipt_number": receipt_number,
                    "updated_at": datetime.now(UTC),
                },
            )

            # Create journal entry for payment
            journal_entry_id = uuid.uuid4()
            db.execute(
                text("""
                INSERT INTO journal_entries (
                    id, organization_id, entry_no, posting_date, reference_type, reference_id,
                    remarks, status, created_by, updated_by, created_at, updated_at
                ) VALUES (
                    :id, :org_id, :entry_no, :posting_date, 'PaymentEntry', :reference_id,
                    :remarks, 'posted', :user_id, :user_id, :created_at, :updated_at
                )
            """),
                {
                    "id": journal_entry_id,
                    "org_id": ORG_ID,
                    "entry_no": f"JE-PAY-{1000 + i}",
                    "posting_date": payment_date,
                    "reference_id": payment_id,
                    "remarks": f"Customer payment {receipt_number}",
                    "user_id": ADMIN_USER_ID,
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
            )

            # Cancel payment
            db.execute(
                text("""
                UPDATE payment_entries
                SET status = 'Cancelled',
                    cancellation_reason = :reason,
                    cancelled_by = :user_id,
                    cancelled_at = :cancelled_at,
                    updated_at = :updated_at
                WHERE id = :payment_id
            """),
                {
                    "payment_id": payment_id,
                    "reason": cancellation_reasons[i],
                    "user_id": ADMIN_USER_ID,
                    "cancelled_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
            )

            # Create reversing journal entry
            reversing_entry_id = uuid.uuid4()
            db.execute(
                text("""
                INSERT INTO journal_entries (
                    id, organization_id, entry_no, posting_date, reference_type, reference_id,
                    remarks, status, created_by, updated_by, created_at, updated_at
                ) VALUES (
                    :id, :org_id, :entry_no, :posting_date, 'PaymentEntry', :reference_id,
                    :remarks, 'posted', :user_id, :user_id, :created_at, :updated_at
                )
            """),
                {
                    "id": reversing_entry_id,
                    "org_id": ORG_ID,
                    "entry_no": f"JE-REV-{1000 + i}",
                    "posting_date": datetime.now(UTC),
                    "reference_id": payment_id,
                    "remarks": f"Reversal of payment {receipt_number} - {cancellation_reasons[i]}",
                    "user_id": ADMIN_USER_ID,
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
            )

            # Remove allocations
            db.execute(
                text("""
                DELETE FROM payment_references WHERE payment_id = :payment_id
            """),
                {"payment_id": payment_id},
            )

            print(f"  ✅ Created cancelled customer payment {i + 1}: {receipt_number}")

        db.commit()

        print("\n📝 Creating 2 cancelled supplier payments...")

        for i in range(2):
            invoice = supplier_invoices[i]
            payment_id = uuid.uuid4()
            payment_amount = invoice.balance_due
            payment_date = datetime.now(UTC) - timedelta(days=10 - i)

            # Create payment entry (Draft)
            db.execute(
                text("""
                INSERT INTO payment_entries (
                    id, organization_id, payment_type, party_id, amount, currency_code,
                    payment_date, payment_mode, reference_no, status, source,
                    created_by, updated_by, created_at, updated_at
                ) VALUES (
                    :id, :org_id, 'Supplier_Payment', :party_id, :amount, 'USD',
                    :payment_date, 'Bank_Transfer', :reference_no, 'Draft', 'Manual',
                    :user_id, :user_id, :created_at, :updated_at
                )
            """),
                {
                    "id": payment_id,
                    "org_id": ORG_ID,
                    "party_id": invoice.supplier_id,
                    "amount": payment_amount,
                    "payment_date": payment_date,
                    "reference_no": f"SUP-CANC-{2000 + i}",
                    "user_id": ADMIN_USER_ID,
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
            )

            # Create allocation
            db.execute(
                text("""
                INSERT INTO payment_references (
                    id, organization_id, payment_id, invoice_id, allocated_amount,
                    exchange_rate, allocated_amount_invoice_currency, created_by, created_at
                ) VALUES (
                    :id, :org_id, :payment_id, :invoice_id, :allocated_amount,
                    1.0, :allocated_amount, :user_id, :created_at
                )
            """),
                {
                    "id": uuid.uuid4(),
                    "org_id": ORG_ID,
                    "payment_id": payment_id,
                    "invoice_id": invoice.id,
                    "allocated_amount": payment_amount,
                    "user_id": ADMIN_USER_ID,
                    "created_at": datetime.now(UTC),
                },
            )

            # Confirm payment
            receipt_number = f"RCP-2026-{2000 + i}"
            db.execute(
                text("""
                UPDATE payment_entries
                SET status = 'Confirmed', receipt_number = :receipt_number, updated_at = :updated_at
                WHERE id = :payment_id
            """),
                {
                    "payment_id": payment_id,
                    "receipt_number": receipt_number,
                    "updated_at": datetime.now(UTC),
                },
            )

            # Create journal entry
            journal_entry_id = uuid.uuid4()
            db.execute(
                text("""
                INSERT INTO journal_entries (
                    id, organization_id, entry_no, posting_date, reference_type, reference_id,
                    remarks, status, created_by, updated_by, created_at, updated_at
                ) VALUES (
                    :id, :org_id, :entry_no, :posting_date, 'PaymentEntry', :reference_id,
                    :remarks, 'posted', :user_id, :user_id, :created_at, :updated_at
                )
            """),
                {
                    "id": journal_entry_id,
                    "org_id": ORG_ID,
                    "entry_no": f"JE-SUPP-{2000 + i}",
                    "posting_date": payment_date,
                    "reference_id": payment_id,
                    "remarks": f"Supplier payment {receipt_number}",
                    "user_id": ADMIN_USER_ID,
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
            )

            # Cancel payment
            db.execute(
                text("""
                UPDATE payment_entries
                SET status = 'Cancelled',
                    cancellation_reason = :reason,
                    cancelled_by = :user_id,
                    cancelled_at = :cancelled_at,
                    updated_at = :updated_at
                WHERE id = :payment_id
            """),
                {
                    "payment_id": payment_id,
                    "reason": cancellation_reasons[3 + i],
                    "user_id": ADMIN_USER_ID,
                    "cancelled_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
            )

            # Create reversing journal entry
            reversing_entry_id = uuid.uuid4()
            db.execute(
                text("""
                INSERT INTO journal_entries (
                    id, organization_id, entry_no, posting_date, reference_type, reference_id,
                    remarks, status, created_by, updated_by, created_at, updated_at
                ) VALUES (
                    :id, :org_id, :entry_no, :posting_date, 'PaymentEntry', :reference_id,
                    :remarks, 'posted', :user_id, :user_id, :created_at, :updated_at
                )
            """),
                {
                    "id": reversing_entry_id,
                    "org_id": ORG_ID,
                    "entry_no": f"JE-SREV-{2000 + i}",
                    "posting_date": datetime.now(UTC),
                    "reference_id": payment_id,
                    "remarks": f"Reversal of supplier payment {receipt_number} - {cancellation_reasons[3 + i]}",
                    "user_id": ADMIN_USER_ID,
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
            )

            # Remove allocations
            db.execute(
                text("""
                DELETE FROM payment_references WHERE payment_id = :payment_id
            """),
                {"payment_id": payment_id},
            )

            print(f"  ✅ Created cancelled supplier payment {i + 1}: {receipt_number}")

        db.commit()

        # Verify results
        print("\n📊 Verification:")

        cancelled_count = db.execute(
            text("""
            SELECT COUNT(*) FROM payment_entries
            WHERE organization_id = :org_id AND status = 'Cancelled'
        """),
            {"org_id": ORG_ID},
        ).scalar()

        reversing_count = db.execute(
            text("""
            SELECT COUNT(*) FROM journal_entries
            WHERE organization_id = :org_id
            AND reference_type = 'PaymentEntry'
            AND remarks LIKE '%Reversal%'
        """),
            {"org_id": ORG_ID},
        ).scalar()

        print(f"  - Total cancelled payments: {cancelled_count}")
        print(f"  - Reversing journal entries: {reversing_count}")

        print("\n" + "=" * 70)
        print("✅ Task 21.4 Complete!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
