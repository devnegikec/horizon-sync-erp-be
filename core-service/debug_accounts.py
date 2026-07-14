"""Debug account lookup"""

import os
import uuid

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/postgres"
)
ORG_ID = uuid.UUID("b1f71de1-0a19-424e-9580-1d3f871c5b1f")

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Check if accounts table exists
    result = conn.execute(
        text("""
        SELECT COUNT(*) FROM accounts
    """)
    )
    count = result.fetchone()[0]
    print(f"Total accounts in database: {count}")

    # Check for account 1110
    result = conn.execute(
        text("""
        SELECT id, account_code, account_name, organization_id
        FROM accounts
        WHERE account_code = '1110'
    """)
    )
    rows = result.fetchall()
    print(f"\nAccounts with code 1110: {len(rows)}")
    for row in rows:
        print(f"  ID: {row[0]}")
        print(f"  Code: {row[1]}")
        print(f"  Name: {row[2]}")
        print(f"  Org ID: {row[3]}")

    # Check with organization filter
    result = conn.execute(
        text("""
        SELECT id, account_code, account_name, organization_id
        FROM accounts
        WHERE organization_id = :org_id AND account_code = :code
    """),
        {"org_id": str(ORG_ID), "code": "1110"},
    )
    rows = result.fetchall()
    print(f"\nAccounts with code 1110 and org {ORG_ID}: {len(rows)}")
    for row in rows:
        print(f"  ID: {row[0]}")
        print(f"  Code: {row[1]}")
        print(f"  Name: {row[2]}")
        print(f"  Org ID: {row[3]}")
