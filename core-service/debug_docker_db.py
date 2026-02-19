"""Debug Docker database connection"""
import os
import uuid
from sqlalchemy import create_engine, text

# Try Docker database URL
DOCKER_DB_URL = "postgresql://horizon_user:horizon_pass@localhost:5432/horizon_erp"
ORG_ID = uuid.UUID("b1f71de1-0a19-424e-9580-1d3f871c5b1f")

print(f"Connecting to: {DOCKER_DB_URL}")

try:
    engine = create_engine(DOCKER_DB_URL)
    
    with engine.connect() as conn:
        # Check if accounts table exists
        result = conn.execute(text("""
            SELECT COUNT(*) FROM accounts
        """))
        count = result.fetchone()[0]
        print(f"Total accounts in database: {count}")
        
        # Check for account 1110
        result = conn.execute(text("""
            SELECT id, account_code, account_name, organization_id 
            FROM accounts 
            WHERE account_code = '1110'
        """))
        rows = result.fetchall()
        print(f"\nAccounts with code 1110: {len(rows)}")
        for row in rows:
            print(f"  ID: {row[0]}")
            print(f"  Code: {row[1]}")
            print(f"  Name: {row[2]}")
            print(f"  Org ID: {row[3]}")
except Exception as e:
    print(f"Error: {e}")
