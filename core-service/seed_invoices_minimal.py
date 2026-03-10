"""Minimal invoice seeding for payment testing"""

import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

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
        print("Creating minimal invoice data for payment testing...")

        # Check if customers exist
        customer_check = text(
            "SELECT id FROM customers WHERE organization_id = :org_id LIMIT 10"
        )
        customers = db.execute(customer_check, {"org_id": ORG_ID}).fetchall()

        if not customers:
            print("\n  Creating 10 test customers...")
            for i in range(10):
                customer_insert = text("""
                    INSERT INTO customers (id, organization_id, customer_name, customer_code, email, phone, status, created_at, updated_at)
                    VALUES (:id, :org_id, :customer_name, :customer_code, :email, :phone, 'active', :created_at, :updated_at)
                """)
                db.execute(
                    customer_insert,
                    {
                        "id": uuid.uuid4(),
                        "org_id": ORG_ID,
                        "customer_name": f"Test Customer {i + 1}",
                        "customer_code": f"CUST-{1000 + i}",
                        "email": f"customer{i + 1}@test.com",
                        "phone": f"+1-555-{1000 + i}",
                        "created_at": datetime.now(UTC),
                        "updated_at": datetime.now(UTC),
                    },
                )
            db.commit()
            customers = db.execute(customer_check, {"org_id": ORG_ID}).fetchall()
            print(f"  ✅ Created {len(customers)} customers")
        else:
            print(f"  ✅ Found {len(customers)} existing customers")

        # Check if suppliers exist
        supplier_check = text(
            "SELECT id FROM suppliers WHERE organization_id = :org_id LIMIT 5"
        )
        suppliers = db.execute(supplier_check, {"org_id": ORG_ID}).fetchall()

        if not suppliers:
            print("\n  Creating 5 test suppliers...")
            for i in range(5):
                supplier_insert = text("""
                    INSERT INTO suppliers (id, organization_id, supplier_name, supplier_code, email, phone, status, created_at, updated_at)
                    VALUES (:id, :org_id, :supplier_name, :supplier_code, :email, :phone, 'active', :created_at, :updated_at)
                """)
                db.execute(
                    supplier_insert,
                    {
                        "id": uuid.uuid4(),
                        "org_id": ORG_ID,
                        "supplier_name": f"Test Supplier {i + 1}",
                        "supplier_code": f"SUPP-{2000 + i}",
                        "email": f"supplier{i + 1}@test.com",
                        "phone": f"+1-555-{2000 + i}",
                        "created_at": datetime.now(UTC),
                        "updated_at": datetime.now(UTC),
                    },
                )
            db.commit()
            suppliers = db.execute(supplier_check, {"org_id": ORG_ID}).fetchall()
            print(f"  ✅ Created {len(suppliers)} suppliers")
        else:
            print(f"  ✅ Found {len(suppliers)} existing suppliers")

        # Create customer invoices
        print("\n  Creating 15 customer invoices...")
        for i, customer in enumerate(customers[:10]):
            for j in range(
                1 if i < 5 else 2
            ):  # 5 customers get 1 invoice, 5 get 2 invoices
                amount = Decimal(str(1000 + (i * 100) + (j * 50)))
                invoice_insert = text("""
                    INSERT INTO invoices (
                        id, organization_id, invoice_no, invoice_date, due_date,
                        invoice_type, status, customer_id, total_amount, balance_due,
                        currency, created_at, updated_at
                    ) VALUES (
                        :id, :org_id, :invoice_no, :invoice_date, :due_date,
                        'SALES', 'Unpaid', :customer_id, :total_amount, :balance_due,
                        'USD', :created_at, :updated_at
                    )
                """)
                db.execute(
                    invoice_insert,
                    {
                        "id": uuid.uuid4(),
                        "org_id": ORG_ID,
                        "invoice_no": f"INV-CUST-{1000 + i}-{j}",
                        "invoice_date": datetime.now(UTC) - timedelta(days=30 - i),
                        "due_date": datetime.now(UTC) + timedelta(days=30),
                        "customer_id": customer.id,
                        "total_amount": amount,
                        "balance_due": amount,
                        "created_at": datetime.now(UTC),
                        "updated_at": datetime.now(UTC),
                    },
                )
        db.commit()
        print("  ✅ Created 15 customer invoices")

        # Create supplier invoices
        print("\n  Creating 5 supplier invoices...")
        for i, supplier in enumerate(suppliers):
            amount = Decimal(str(2000 + (i * 200)))
            invoice_insert = text("""
                INSERT INTO invoices (
                    id, organization_id, invoice_no, invoice_date, due_date,
                    invoice_type, status, supplier_id, total_amount, balance_due,
                    currency, created_at, updated_at
                ) VALUES (
                    :id, :org_id, :invoice_no, :invoice_date, :due_date,
                    'PURCHASE', 'Unpaid', :supplier_id, :total_amount, :balance_due,
                    'USD', :created_at, :updated_at
                )
            """)
            db.execute(
                invoice_insert,
                {
                    "id": uuid.uuid4(),
                    "org_id": ORG_ID,
                    "invoice_no": f"INV-SUPP-{2000 + i}",
                    "invoice_date": datetime.now(UTC) - timedelta(days=20 - i),
                    "due_date": datetime.now(UTC) + timedelta(days=30),
                    "supplier_id": supplier.id,
                    "total_amount": amount,
                    "balance_due": amount,
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
            )
        db.commit()
        print("  ✅ Created 5 supplier invoices")

        # Verify
        customer_inv_count = db.execute(
            text("""
            SELECT COUNT(*) FROM invoices
            WHERE organization_id = :org_id AND invoice_type = 'SALES' AND balance_due > 0
        """),
            {"org_id": ORG_ID},
        ).scalar()

        supplier_inv_count = db.execute(
            text("""
            SELECT COUNT(*) FROM invoices
            WHERE organization_id = :org_id AND invoice_type = 'PURCHASE' AND balance_due > 0
        """),
            {"org_id": ORG_ID},
        ).scalar()

        print("\n✅ Invoice seeding complete!")
        print(f"   - Customer invoices: {customer_inv_count}")
        print(f"   - Supplier invoices: {supplier_inv_count}")
        print("\nReady to run payment seed script!")

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
