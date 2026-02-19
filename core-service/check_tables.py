"""Check if journal entry tables exist"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/postgres")

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'journal%'
        ORDER BY table_name
    """))
    
    tables = result.fetchall()
    
    if tables:
        print("Journal entry tables found:")
        for table in tables:
            print(f"  - {table[0]}")
    else:
        print("No journal entry tables found in the database")
    
    # Also check for the enum type
    result = conn.execute(text("""
        SELECT typname 
        FROM pg_type 
        WHERE typname = 'journalstatus'
    """))
    
    enum_type = result.fetchone()
    if enum_type:
        print(f"\nEnum type 'journalstatus' exists")
    else:
        print(f"\nEnum type 'journalstatus' does NOT exist")
