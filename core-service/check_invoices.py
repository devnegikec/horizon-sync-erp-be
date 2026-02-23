"""Check invoice data"""
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://horizon_user:horizon_pass@localhost:5432/core_db')
engine = create_engine(DATABASE_URL)
conn = engine.connect()

result = conn.execute(
    text('SELECT invoice_no, invoice_type, total_amount, balance_due, status FROM invoices WHERE organization_id = :org_id ORDER BY created_at DESC LIMIT 20'),
    {'org_id': 'b1f71de1-0a19-424e-9580-1d3f871c5b1f'}
)

print("Recent Invoices:")
for row in result:
    print(f"  {row.invoice_no}: {row.invoice_type} - Total: ${row.total_amount}, Balance: ${row.balance_due}, Status: {row.status}")

conn.close()
