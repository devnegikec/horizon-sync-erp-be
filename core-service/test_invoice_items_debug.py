"""Debug script to check invoice items in database"""
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def check_invoice_items():
    db = SessionLocal()
    try:
        # Get the most recent invoice
        result = db.execute(text("""
            SELECT id, invoice_no, grand_total, status
            FROM invoices
            ORDER BY created_at DESC
            LIMIT 1
        """))
        invoice = result.fetchone()
        
        if not invoice:
            print("No invoices found in database")
            return
        
        print(f"\nMost recent invoice:")
        print(f"  ID: {invoice[0]}")
        print(f"  Invoice No: {invoice[1]}")
        print(f"  Grand Total: {invoice[2]}")
        print(f"  Status: {invoice[3]}")
        
        # Check if this invoice has items
        result = db.execute(text("""
            SELECT id, item_code, item_name, qty, rate, amount, 
                   tax_amount, discount_amount, total_amount
            FROM invoice_items
            WHERE invoice_id = :invoice_id
        """), {"invoice_id": invoice[0]})
        
        items = result.fetchall()
        
        if not items:
            print(f"\n❌ NO ITEMS FOUND for invoice {invoice[1]}")
        else:
            print(f"\n✅ Found {len(items)} items:")
            for item in items:
                print(f"  - {item[1]} ({item[2]}): qty={item[3]}, rate={item[4]}, amount={item[5]}")
                print(f"    tax={item[6]}, discount={item[7]}, total={item[8]}")
        
        # Check if invoice_items table has the new columns
        result = db.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'invoice_items'
            AND column_name IN ('tax_template_id', 'tax_rate', 'tax_amount', 
                               'discount_type', 'discount_value', 'discount_amount', 'total_amount')
            ORDER BY column_name
        """))
        
        columns = result.fetchall()
        print(f"\n✅ Tax/Discount columns in invoice_items table:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_invoice_items()
