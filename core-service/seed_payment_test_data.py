"""
Seed script for payment testing data.
Creates customers, invoices, and sample payments for testing the payment system.
"""

import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)


def seed_payment_test_data():
    """Create test data for payment system"""
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        print("\n" + "="*60)
        print("PAYMENT SYSTEM TEST DATA SEEDING")
        print("="*60 + "\n")

        # Get organization ID from default_accounts
        result = db.execute(text("SELECT DISTINCT organization_id FROM default_accounts LIMIT 1"))
        org_row = result.fetchone()
        
        if not org_row:
            print("❌ No organization found in default_accounts.")
            print("   Please ensure default accounts are configured first.")
            return
        
        org_id = org_row[0]
        print(f"✓ Using Organization ID: {org_id}\n")

        # Create test user ID (you can replace with actual user ID)
        user_id = str(uuid4())
        print(f"✓ Using User ID: {user_id}\n")

        # ============================================================
        # STEP 1: Get or Create Customers
        # ============================================================
        print("STEP 1: Getting or Creating Customers")
        print("-" * 60)

        # Check if customers already exist
        result = db.execute(text("""
            SELECT id, customer_code, customer_name 
            FROM customers 
            WHERE organization_id = :org_id 
            AND customer_code IN ('CUST-001', 'CUST-002', 'CUST-003')
            ORDER BY customer_code
        """), {"org_id": org_id})
        
        existing_customers = {row[1]: {"id": str(row[0]), "customer_code": row[1], "customer_name": row[2]} 
                             for row in result.fetchall()}

        customers_data = [
            {
                "customer_code": "CUST-001",
                "customer_name": "ABC Corporation",
                "email": "contact@abccorp.com",
                "phone": "+1-555-0101",
                "address": "123 Business St, New York, NY 10001",
                "credit_limit": Decimal("50000.00"),
            },
            {
                "customer_code": "CUST-002",
                "customer_name": "XYZ Industries",
                "email": "info@xyzind.com",
                "phone": "+1-555-0102",
                "address": "456 Commerce Ave, Los Angeles, CA 90001",
                "credit_limit": Decimal("75000.00"),
            },
            {
                "customer_code": "CUST-003",
                "customer_name": "Tech Solutions Inc",
                "email": "sales@techsolutions.com",
                "phone": "+1-555-0103",
                "address": "789 Innovation Dr, San Francisco, CA 94102",
                "credit_limit": Decimal("100000.00"),
            },
        ]

        customers = []
        for customer_data in customers_data:
            if customer_data["customer_code"] in existing_customers:
                # Use existing customer
                customer = existing_customers[customer_data["customer_code"]]
                customers.append(customer)
                print(f"  ✓ Using existing customer: {customer['customer_name']} ({customer['customer_code']})")
            else:
                # Create new customer
                customer_id = str(uuid4())
                db.execute(text("""
                    INSERT INTO customers (
                        id, organization_id, customer_code, customer_name, 
                        email, phone, address, credit_limit,
                        status, outstanding_balance,
                        created_by, updated_by, created_at, updated_at
                    ) VALUES (
                        :id, :org_id, :customer_code, :customer_name,
                        :email, :phone, :address, :credit_limit,
                        'active', 0.00,
                        :user_id, :user_id, NOW(), NOW()
                    )
                """), {
                    "id": customer_id,
                    **customer_data,
                    "org_id": org_id,
                    "user_id": user_id,
                })
                customers.append({
                    "id": customer_id,
                    "customer_code": customer_data["customer_code"],
                    "customer_name": customer_data["customer_name"],
                })
                print(f"  ✓ Created customer: {customer_data['customer_name']} ({customer_data['customer_code']})")

        print()

        # ============================================================
        # STEP 2: Create Invoices
        # ============================================================
        print("STEP 2: Creating Invoices")
        print("-" * 60)

        today = datetime.now().date()
        
        invoices = [
            {
                "id": str(uuid4()),
                "customer_id": customers[0]["id"],
                "invoice_number": "INV-2026-001",
                "invoice_date": today - timedelta(days=30),
                "due_date": today - timedelta(days=0),  # Due today
                "subtotal": Decimal("5000.00"),
                "tax_amount": Decimal("500.00"),
                "total_amount": Decimal("5500.00"),
                "paid_amount": Decimal("0.00"),
                "balance_due": Decimal("5500.00"),
                "status": "unpaid",
                "description": "Website Development Services - Phase 1",
            },
            {
                "id": str(uuid4()),
                "customer_id": customers[0]["id"],
                "invoice_number": "INV-2026-002",
                "invoice_date": today - timedelta(days=15),
                "due_date": today + timedelta(days=15),  # Due in 15 days
                "subtotal": Decimal("3000.00"),
                "tax_amount": Decimal("300.00"),
                "total_amount": Decimal("3300.00"),
                "paid_amount": Decimal("0.00"),
                "balance_due": Decimal("3300.00"),
                "status": "unpaid",
                "description": "Website Development Services - Phase 2",
            },
            {
                "id": str(uuid4()),
                "customer_id": customers[1]["id"],
                "invoice_number": "INV-2026-003",
                "invoice_date": today - timedelta(days=45),
                "due_date": today - timedelta(days=15),  # Overdue
                "subtotal": Decimal("8000.00"),
                "tax_amount": Decimal("800.00"),
                "total_amount": Decimal("8800.00"),
                "paid_amount": Decimal("0.00"),
                "balance_due": Decimal("8800.00"),
                "status": "overdue",
                "description": "Manufacturing Equipment - Model X200",
            },
            {
                "id": str(uuid4()),
                "customer_id": customers[1]["id"],
                "invoice_number": "INV-2026-004",
                "invoice_date": today - timedelta(days=10),
                "due_date": today + timedelta(days=20),  # Due in 20 days
                "subtotal": Decimal("4500.00"),
                "tax_amount": Decimal("450.00"),
                "total_amount": Decimal("4950.00"),
                "paid_amount": Decimal("0.00"),
                "balance_due": Decimal("4950.00"),
                "status": "unpaid",
                "description": "Maintenance Services - Q1 2026",
            },
            {
                "id": str(uuid4()),
                "customer_id": customers[2]["id"],
                "invoice_number": "INV-2026-005",
                "invoice_date": today - timedelta(days=5),
                "due_date": today + timedelta(days=25),  # Due in 25 days
                "subtotal": Decimal("12000.00"),
                "tax_amount": Decimal("1200.00"),
                "total_amount": Decimal("13200.00"),
                "paid_amount": Decimal("0.00"),
                "balance_due": Decimal("13200.00"),
                "status": "unpaid",
                "description": "Software License - Enterprise Plan (Annual)",
            },
        ]

        for invoice in invoices:
            db.execute(text("""
                INSERT INTO invoices (
                    id, organization_id, customer_id, invoice_number,
                    invoice_date, due_date, subtotal, tax_amount, total_amount,
                    paid_amount, balance_due, status, description,
                    currency_code, created_by, updated_by, created_at, updated_at
                ) VALUES (
                    :id, :org_id, :customer_id, :invoice_number,
                    :invoice_date, :due_date, :subtotal, :tax_amount, :total_amount,
                    :paid_amount, :balance_due, :status, :description,
                    'USD', :user_id, :user_id, NOW(), NOW()
                )
            """), {
                **invoice,
                "org_id": org_id,
                "user_id": user_id,
            })
            print(f"  ✓ Created invoice: {invoice['invoice_number']} - ${invoice['total_amount']} ({invoice['status']})")

        print()

        # Commit all changes
        db.commit()

        print("="*60)
        print("✅ SEEDING COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\nTest Data Summary:")
        print(f"  • Customers: {len(customers)}")
        print(f"  • Invoices: {len(invoices)}")
        print(f"  • Total Invoice Amount: ${sum(inv['total_amount'] for inv in invoices)}")
        print()
        print("Next steps:")
        print("1. Restart backend server (if running)")
        print("2. Go to Revenue > Payments in the UI")
        print("3. Create a payment and allocate to invoices")
        print("4. Confirm the payment")
        print("5. Go to Books > Journal Entries to see the journal entry")
        print()
        print("Test Scenarios:")
        print("  • Full Payment: Pay INV-2026-002 ($3,300) in full")
        print("  • Partial Payment: Pay $2,000 towards INV-2026-001 ($5,500)")
        print("  • Multiple Invoices: Pay $10,000 split across multiple invoices")
        print("  • Overpayment: Pay $6,000 towards INV-2026-001 ($5,500 balance)")
        print()

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR during seeding: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_payment_test_data()
