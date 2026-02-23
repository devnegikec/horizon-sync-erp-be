"""Check customer table columns"""

import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db")

def main():
    engine = create_engine(DATABASE_URL)
    
    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'customers'
            ORDER BY ordinal_position
        """))
        
        print("Customers table columns:")
        print("-" * 50)
        for row in result:
            print(f"  {row.column_name:30} {row.data_type}")
        
        print("\n")
        
        result2 = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'suppliers'
            ORDER BY ordinal_position
        """))
        
        print("Suppliers table columns:")
        print("-" * 50)
        for row in result2:
            print(f"  {row.column_name:30} {row.data_type}")

if __name__ == "__main__":
    main()
