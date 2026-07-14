"""Check customers table columns"""

from sqlalchemy import create_engine, text

engine = create_engine("postgresql://horizon_user:horizon_pass@localhost:5432/core_db")
conn = engine.connect()
result = conn.execute(
    text("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'customers'
    ORDER BY ordinal_position
""")
)

print("Customers table columns:")
for row in result.fetchall():
    print(f"  {row[0]} ({row[1]})")
