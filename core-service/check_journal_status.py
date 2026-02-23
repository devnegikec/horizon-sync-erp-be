"""Check journal entry status enum values"""

import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db")

def main():
    engine = create_engine(DATABASE_URL)
    
    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT unnest(enum_range(NULL::journalstatus))::text AS status_value
        """))
        
        print("Journal Status enum values:")
        print("-" * 50)
        for row in result:
            print(f"  {row.status_value}")

if __name__ == "__main__":
    main()
