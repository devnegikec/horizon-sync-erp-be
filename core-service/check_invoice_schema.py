"""Check invoice table schema"""

import os

from sqlalchemy import create_engine, inspect

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

# Get invoices table columns
columns = inspector.get_columns("invoices")
print("Invoices table columns:")
for col in columns:
    print(f"  {col['name']}: {col['type']}")
