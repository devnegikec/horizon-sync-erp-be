"""Check invoice_items table schema"""
from sqlalchemy import create_engine, inspect
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://horizon_user:horizon_pass@localhost:5432/core_db')
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

# Get invoice_items table columns
columns = inspector.get_columns('invoice_items')
print('Invoice Items table columns:')
for col in columns:
    print(f"  {col['name']}: {col['type']}")
