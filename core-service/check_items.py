"""Check items in database"""

import os

from sqlalchemy import create_engine, inspect

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

# Get items table columns
print("Items table columns:")
columns = inspector.get_columns("items")
for col in columns:
    print(f"  {col['name']}: {col['type']}")

# Get some sample items
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM items LIMIT 5"))
    items = result.fetchall()

    print(f"\nFound {len(items)} sample items")
    if items:
        print("Sample item IDs:", [str(item.id) for item in items])
