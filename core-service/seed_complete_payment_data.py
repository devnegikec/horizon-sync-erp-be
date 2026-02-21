"""Complete Payment Data Seeding Script

Seeds:
1. Invoice items for existing invoices
2. Draft payments (unallocated)
3. Draft payments with allocations
4. Supplier payments

Usage:
    python seed_complete_payment_data.py
"""

import os
import sys
import uuid
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db")

# Organization and User IDs
ORG_ID = uuid.UUID("b1f71de1-0a19-424e-9580-1d3f871c5b1f")
ADMIN_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def seed_invoice_items(db: Session, org_id: uuid.UUID):
    """Seed invoice items for existing invoices"""
    print("\n=== Seeding Invoice Items ===\n")
    
    # Get available items
    items_query = text("""
        SELECT id FROM items 
        WHERE organization_id = :org_id 
        LIMIT 10
    """)
    available_items = db.execute(items_query, {"org_id": org_id}).fetchall()
    
    if not available_items:
        print("  No items available in database. Skipping invoice items seeding.")
        return 0
    
    item_ids = [item.id for item in available_items]
    print(f"  Found {len(item_ids)} available items")
    
    # Get invoices without items
    query = text("""
        SELECT i.id, i.invoice_no, i.total_amount, i.invoice_type
        FROM invoices i
        LEFT JOIN invoice_items ii ON i.id = ii.invoice_id
        WHERE i.organization_id = :org_id
        AND ii.id IS NULL
        LIMIT 20
    """)
    
    invoices = db.execute(query, {"org_id": org_id}).fetchall()
    
    if not invoices:
        print("  No invoices need items. Skipping.")
        return 0
    
    items_created = 0
    
    for invoice in invoices:
        try:
            # Create 2-3 items per invoice
            num_items = 2 if items_created < 10 else 3
            item_amount = Decimal(str(invoice.total_amount)) / num_items
            
            for i in range(num_items):
                # Use a rotating item_id from available items
                item_id = item_ids[items_created % len(item_ids)]
                
                item_data = {
                    "id": uuid.uuid4(),
                    "invoice_id": invoice.id,
                    "organization_id": org_id,
                    "item_id": item_id,
                    "description": f"Test item {i+1} for {invoice.invoice_no}",
                    "quantity": Decimal("1.00"),
                    "unit_price": item_amount,
                    "tax_rate": Decimal("0.00"),
                    "tax_amount": Decimal("0.00"),
                    "total_amount": item_amount,
                }
                
                insert_query = text("""
                    INSERT INTO invoice_items 
                    (id, invoice_id, organization_id, item_id, description, quantity, unit_price, tax_rate, tax_amount, total_amount)
                    VALUES 
                    (:id, :invoice_id, :organization_id, :item_id, :description, :quantity, :unit_price, :tax_rate, :tax_amount, :total_amount)
                """)
                
                db.execute(insert_query, item_data)
                items_created += 1
            
            print(f"  Created {num_items} items for invoice {invoice.invoice_no}")
            
        except Exception as e:
            print(f"  Error creating items for invoice {invoice.invoice_no}: {str(e)}")
            db.rollback()
            continue
    
    db.commit()
    print(f"\n  Total invoice items created: {items_created}")
    return items_created


def get_unpaid_invoices(db: Session, org_id: uuid.UUID, invoice_type: str, limit: int = 20):
    """Get unpaid invoices"""
    query = text("""
        SELECT id, customer_id, supplier_id, total_amount, balance_due, invoice_no, invoice_type
        FROM invoices
        WHERE organization_id = :org_id
        AND invoice_type = :invoice_type
        AND balance_due > 0
        ORDER BY created_at
        LIMIT :limit
    """)
    return db.execute(query, {"org_id": org_id, "invoice_type": invoice_type, "limit": limit}).fetchall()


def create_draft_payments_unallocated(db: Session, org_id: uuid.UUID, admin_user_id: uuid.UUID):
    """Create draft payments without allocations"""
    from app.services.payment_entry_service import PaymentEntryService
    from app.models.base import PaymentEntryType, PaymentMode
    from app.schemas.payment_entry import PaymentEntryCreate
    
    print("\n=== Creating Draft Payments (Unallocated) ===\n")
    
    payment_service = PaymentEntryService(db)
    customer_invoices = get_unpaid_invoices(db, org_id, 'SALES', 5)
    
    if not customer_invoices:
        print("  No customer invoices available.")
        return 0
    
    draft_count = 0
    payment_modes = [PaymentMode.CASH, PaymentMode.CHECK, PaymentMode.BANK_TRANSFER]
    
    for i, invoice in enumerate(customer_invoices[:5]):
        try:
            payment_mode = payment_modes[i % 3]
            party_id = invoice.customer_id if invoice.invoice_type == 'SALES' else invoice.supplier_id
            
            payment_data = PaymentEntryCreate(
                payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
                party_id=party_id,
                amount=Decimal(str(invoice.balance_due)),
                currency_code="USD",
                payment_date=datetime.now(UTC) - timedelta(days=i),
                payment_mode=payment_mode,
                reference_no=f"DRAFT-{8000 + i}" if payment_mode != PaymentMode.CASH else None
            )
            
            payment = payment_service.create_payment_entry(
                data=payment_data,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            draft_count += 1
            print(f"  Created draft payment {payment.id} - ${payment.amount} ({payment_mode.value})")
            
        except Exception as e:
            print(f"  Error creating draft payment: {str(e)}")
            db.rollback()
            continue
    
    db.commit()
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
    customer_invoices = get_unpaid_invoices(db, org_id, 'SALES', 15)
    
    if len(customer_invoices) < 5:
        print(f"  Only {len(customer_invoices)} invoices available.")
        return 0
    
    allocated_count = 0
    
    for i, invoice in enumerate(customer_invoices[5:10]):
        try:
            payment_mode = PaymentMode.BANK_TRANSFER if i % 2 == 0 else PaymentMode.CHECK
            party_id = invoice.customer_id if invoice.invoice_type == 'SALES' else invoice.supplier_id
            
            payment_data = PaymentEntryCreate(
                payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
                party_id=party_id,
                amount=Decimal(str(invoice.balance_due)),
                currency_code="USD",
                payment_date=datetime.now(UTC) - timedelta(days=5 + i),
                payment_mode=payment_mode,
                reference_no=f"ALLOC-{9000 + i}"
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
            
            allocated_count += 1
            print(f"  Created payment {payment.id} with allocation to {invoice.invoice_no} - ${payment.amount}")
            
        except Exception as e:
            print(f"  Error creating allocated payment: {str(e)}")
            db.rollback()
            continue
    
    db.commit()
    print(f"\n  Total payments with allocations created: {allocated_count}")
    return allocated_count


def create_supplier_payments(db: Session, org_id: uuid.UUID, admin_user_id: uuid.UUID):
    """Create supplier payments"""
    from app.services.payment_entry_service import PaymentEntryService
    from app.services.allocation_service import AllocationService
    from app.models.base import PaymentEntryType, PaymentMode
    from app.schemas.payment_entry import PaymentEntryCreate
    
    print("\n=== Creating Supplier Payments ===\n")
    
    payment_service = PaymentEntryService(db)
    allocation_service = AllocationService(db)
    supplier_invoices = get_unpaid_invoices(db, org_id, 'PURCHASE', 10)
    
    if not supplier_invoices:
        print("  No supplier invoices available.")
        return 0
    
    supplier_count = 0
    
    # Create 3 draft supplier payments
    for i, invoice in enumerate(supplier_invoices[:3]):
        try:
            party_id = invoice.supplier_id
            
            payment_data = PaymentEntryCreate(
                payment_type=PaymentEntryType.SUPPLIER_PAYMENT,
                party_id=party_id,
                amount=Decimal(str(invoice.balance_due)),
                currency_code="USD",
                payment_date=datetime.now(UTC) - timedelta(days=i),
                payment_mode=PaymentMode.BANK_TRANSFER,
                reference_no=f"SUP-{10000 + i}"
            )
            
            payment = payment_service.create_payment_entry(
                data=payment_data,
                organization_id=org_id,
                user_id=admin_user_id
            )
            
            supplier_count += 1
            print(f"  Created draft supplier payment {payment.id} - ${payment.amount}")
            
        except Exception as e:
            print(f"  Error creating supplier payment: {str(e)}")
            db.rollback()
            continue
    
    # Create 2 supplier payments with allocations
    for i, invoice in enumerate(supplier_invoices[3:5]):
        try:
            party_id = invoice.supplier_id
            
            payment_data = PaymentEntryCreate(
                payment_type=PaymentEntryType.SUPPLIER_PAYMENT,
                party_id=party_id,
                amount=Decimal(str(invoice.balance_due)),
                currency_code="USD",
                payment_date=datetime.now(UTC) - timedelta(days=10 + i),
                payment_mode=PaymentMode.BANK_TRANSFER,
                reference_no=f"SUP-ALLOC-{11000 + i}"
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
            
            supplier_count += 1
            print(f"  Created supplier payment {payment.id} with allocation - ${payment.amount}")
            
        except Exception as e:
            print(f"  Error creating allocated supplier payment: {str(e)}")
            db.rollback()
            continue
    
    db.commit()
    print(f"\n  Total supplier payments created: {supplier_count}")
    return supplier_count


def print_summary(db: Session, org_id: uuid.UUID):
    """Print summary of seeded data"""
    print("\n" + "=" * 70)
    print("COMPLETE PAYMENT DATA SEEDING SUMMARY")
    print("=" * 70)
    
    # Count invoice items
    items_query = text("""
        SELECT COUNT(*) as count
        FROM invoice_items
        WHERE organization_id = :org_id
    """)
    items_count = db.execute(items_query, {"org_id": org_id}).scalar()
    print(f"\nTotal Invoice Items: {items_count}")
    
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
    
    # Count allocations
    allocation_query = text("""
        SELECT COUNT(*) as count
        FROM payment_references
        WHERE organization_id = :org_id
    """)
    allocation_count = db.execute(allocation_query, {"org_id": org_id}).scalar()
    
    print(f"\nTotal Payment Allocations: {allocation_count}")
    
    # Count unpaid invoices
    unpaid_query = text("""
        SELECT invoice_type, COUNT(*) as count
        FROM invoices
        WHERE organization_id = :org_id
        AND balance_due > 0
        GROUP BY invoice_type
    """)
    unpaid_counts = db.execute(unpaid_query, {"org_id": org_id}).fetchall()
    
    print("\nRemaining Unpaid Invoices:")
    for row in unpaid_counts:
        print(f"  {row.invoice_type}: {row.count}")
    
    print("\n" + "=" * 70)


def main():
    """Main seeding function"""
    print("=" * 70)
    print("COMPLETE PAYMENT DATA SEEDING")
    print("=" * 70)
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print(f"\nOrganization ID: {ORG_ID}")
        print(f"Admin User ID: {ADMIN_USER_ID}")
        
        # Seed invoice items
        items_count = seed_invoice_items(db, ORG_ID)
        
        # Seed payments
        draft_count = create_draft_payments_unallocated(db, ORG_ID, ADMIN_USER_ID)
        allocated_count = create_draft_payments_with_allocations(db, ORG_ID, ADMIN_USER_ID)
        supplier_count = create_supplier_payments(db, ORG_ID, ADMIN_USER_ID)
        
        # Print summary
        print_summary(db, ORG_ID)
        
        print("\nSeeding completed successfully!")
        
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
