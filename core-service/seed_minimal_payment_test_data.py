"""
Minimal seed data for payment system testing.
Creates just enough data to test the complete payment flow.
"""

import os
import sys
import uuid
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)


def seed_minimal_payment_test_data():
    """Seed minimal test data for payment system"""
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        print("\n" + "="*60)
        print("SEEDING MINIMAL PAYMENT TEST DATA")
        print("="*60 + "\n")

        # Get organization and user IDs
        result = db.execute(text("SELECT id FROM organizations LIMIT 1"))
        org_row = result.fetchone()
        
        if not org_row:
            print("❌ No organization found. Please create an organization first.")
            return
        
        org_id = org_row[0]
        print(f"✓ Using Organization ID: {org_id}")

        result = db.execute(text("SELECT id FROM users LIMIT 1"))
        user_row = result.fetchone()
        
        if not user_row:
            print("❌ No user found. Please create a user first.")
            return
        
        user_id = user_row[0]
        print(f"✓ Using User ID: {user_id}\n")

        # ============================================================
        # 1. CREATE CUSTOMERS
        # ============================================================
        print("1. Creating test customers...")
        
        customers = [
            {
                "id": str(uuid.uuid4()),
                "customer_name": "ABC Corporation",
                "customer_code": "CUST-001",
                "email": "contact@abccorp.com",
                "phone": "+1-555-0101",
                "address": "123 Business St, New York, NY 10001",
            },
            {
                "id": str(uuid.uuid4()),
                "customer_name": "XYZ Limited",
                "customer_code": "CUST-002",
                "email": "info@xyzltd.com",
                "phone": "+1-555-0102",
                "address": "456 Commerce Ave, Los Angeles, CA 90001",
            },
        ]

        for customer in customers:
            db.execute(text("""
                INSERT INTO customers (
                    id, organization_id, customer_name, customer_code,
                    email, phone, address, created_at, updated_at
                ) VALUES (
                    :id, :org_id, :customer_name, :customer_code,
                    :email, :phone, :address, :created_at, :updated_at
                )
            """), {
                "id": customer["id"],
                "org_id": org_id,
                "customer_name": customer["customer_name"],
                "customer_code": customer["customer_code"],
                "email": customer["email"],
                "phone": customer["phone"],
                "address": customer["address"],
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            })
            print(f"   ✓ Created customer: {customer['customer_name']} ({customer['customer_code']})")
        
        print()

        # ============================================================
        # 2. CREATE INVOICES
        # ============================================================
        print("2. Creating test invoices...")
        
        today = datetime.now(UTC)
        
        invoices = [
            {
                "id": str(uuid.uuid4()),
                "customer_id": customers[0]["id"],  # ABC Corporation
                "invoice_no": "INV-2026-001",
                "invoice_date": today - timedelta(days=10),
                "due_date": today + timedelta(days=20),
                "subtotal": Decimal("900.00"),
                "tax_amount": Decimal("100.00"),
                "grand_total": Decimal("1000.00"),
                "outstanding_amount": Decimal("1000.00"),
                "status": "draft",  # Unpaid
                "description": "Website Development Services",
            },
            {
                "id": str(uuid.uuid4()),
                "customer_id": customers[0]["id"],  # ABC Corporation
                "invoice_no": "INV-2026-002",
                "invoice_date": today - timedelta(days=5),
                "due_date": today + timedelta(days=25),
                "subtotal": Decimal("450.00"),
                "tax_amount": Decimal("50.00"),
                "grand_total": Decimal("500.00"),
                "outstanding_amount": Decimal("500.00"),
                "status": "draft",  # Unpaid
                "description": "Monthly Maintenance - January",
            },
            {
                "id": str(uuid.uuid4()),
                "customer_id": customers[1]["id"],  # XYZ Limited
                "invoice_no": "INV-2026-003",
                "invoice_date": today - timedelta(days=3),
                "due_date": today + timedelta(days=27),
                "subtotal": Decimal("675.00"),
                "tax_amount": Decimal("75.00"),
                "grand_total": Decimal("750.00"),
                "outstanding_amount": Decimal("750.00"),
                "status": "draft",  # Unpaid
                "description": "Consulting Services - Q1",
            },
        ]

        for invoice in invoices:
            db.execute(text("""
                INSERT INTO invoices (
                    id, organization_id, customer_id, invoice_no,
                    invoice_date, due_date, subtotal, tax_amount,
                    grand_total, outstanding_amount, status,
                    notes, created_at, updated_at
                ) VALUES (
                    :id, :org_id, :customer_id, :invoice_no,
                    :invoice_date, :due_date, :subtotal, :tax_amount,
                    :grand_total, :outstanding_amount, :status,
                    :notes, :created_at, :updated_at
                )
            """), {
                "id": invoice["id"],
                "org_id": org_id,
                "customer_id": invoice["customer_id"],
                "invoice_no": invoice["invoice_no"],
                "invoice_date": invoice["invoice_date"],
                "due_date": invoice["due_date"],
                "subtotal": invoice["subtotal"],
                "tax_amount": invoice["tax_amount"],
                "grand_total": invoice["grand_total"],
                "outstanding_amount": invoice["outstanding_amount"],
                "status": invoice["status"],
                "notes": invoice["description"],
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            })
            print(f"   ✓ Created invoice: {invoice['invoice_no']} - ${invoice['grand_total']} ({invoice['description']})")
        
        print()

        # ============================================================
        # 3. CREATE INVOICE ITEMS (Optional but recommended)
        # ============================================================
        print("3. Creating invoice items...")
        
        invoice_items = [
            # Items for Invoice 1 (INV-2026-001)
            {
                "id": str(uuid.uuid4()),
                "invoice_id": invoices[0]["id"],
                "description": "Frontend Development",
                "quantity": Decimal("40.00"),
                "unit_price": Decimal("15.00"),
                "amount": Decimal("600.00"),
            },
            {
                "id": str(uuid.uuid4()),
                "invoice_id": invoices[0]["id"],
                "description": "Backend Development",
                "quantity": Decimal("20.00"),
                "unit_price": Decimal("15.00"),
                "amount": Decimal("300.00"),
            },
            # Items for Invoice 2 (INV-2026-002)
            {
                "id": str(uuid.uuid4()),
                "invoice_id": invoices[1]["id"],
                "description": "Monthly Maintenance",
                "quantity": Decimal("1.00"),
                "unit_price": Decimal("450.00"),
                "amount": Decimal("450.00"),
            },
            # Items for Invoice 3 (INV-2026-003)
            {
                "id": str(uuid.uuid4()),
                "invoice_id": invoices[2]["id"],
                "description": "Business Consulting",
                "quantity": Decimal("15.00"),
                "unit_price": Decimal("45.00"),
                "amount": Decimal("675.00"),
            },
        ]

        for item in invoice_items:
            db.execute(text("""
                INSERT INTO invoice_items (
                    id, invoice_id, description, quantity,
                    unit_price, amount, created_at, updated_at
                ) VALUES (
                    :id, :invoice_id, :description, :quantity,
                    :unit_price, :amount, :created_at, :updated_at
                )
            """), {
                "id": item["id"],
                "invoice_id": item["invoice_id"],
                "description": item["description"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "amount": item["amount"],
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            })
        
        print(f"   ✓ Created {len(invoice_items)} invoice items\n")

        # Commit all changes
        db.commit()

        # ============================================================
        # SUMMARY
        # ============================================================
        print("="*60)
        print("✅ SEED DATA CREATED SUCCESSFULLY")
        print("="*60)
        print("\nTest Data Summary:")
        print("\n📋 CUSTOMERS:")
        for customer in customers:
            print(f"   • {customer['customer_name']} ({customer['customer_code']})")
        
        print("\n📄 INVOICES:")
        for invoice in invoices:
            customer_name = next(c["customer_name"] for c in customers if c["id"] == invoice["customer_id"])
            print(f"   • {invoice['invoice_no']}: ${invoice['grand_total']} - {customer_name}")
            print(f"     Status: Unpaid | Outstanding: ${invoice['outstanding_amount']}")
        
        print("\n" + "="*60)
        print("READY FOR TESTING!")
        print("="*60)
        print("\nYou can now:")
        print("1. Start the backend server")
        print("2. Open the frontend application")
        print("3. Navigate to Revenue > Payments")
        print("4. Follow the testing guide in PAYMENT_BANKING_TESTING_GUIDE.md")
        print()

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR during seeding: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_minimal_payment_test_data()
