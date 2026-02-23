"""Test invoice query"""
from sqlalchemy import create_engine, text
import os
import uuid

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://horizon_user:horizon_pass@localhost:5432/core_db')
ORG_ID = uuid.UUID("b1f71de1-0a19-424e-9580-1d3f871c5b1f")

engine = create_engine(DATABASE_URL)
conn = engine.connect()

query = text("""
    SELECT id, customer_id, total_amount, balance_due, invoice_no
    FROM invoices
    WHERE organization_id = :org_id
    AND invoice_type = 'SALES'
    AND balance_due > 0
    ORDER BY created_at
    LIMIT 20
""")

result = conn.execute(query, {"org_id": ORG_ID})
rows = result.fetchall()

print(f"Found {len(rows)} unpaid customer invoices:")
for row in rows:
    print(f"  {row.invoice_no}: customer_id={row.customer_id}, total=${row.total_amount}, balance=${row.balance_due}")

conn.close()
