"""Check if account exists"""

from sqlalchemy import create_engine, text

engine = create_engine("postgresql://horizon_user:horizon_pass@localhost:5432/core_db")
conn = engine.connect()

account_id = "8120b2db-76b0-4cbb-a745-e94e69c9f88c"

# Check in accounts table
result = conn.execute(
    text(
        f"SELECT id, account_code, account_name FROM accounts WHERE id = '{account_id}'"
    )
)
row = result.fetchone()

if row:
    print("✅ Account EXISTS in accounts table:")
    print(f"   ID: {row[0]}")
    print(f"   Code: {row[1]}")
    print(f"   Name: {row[2]}")
else:
    print("❌ Account NOT FOUND in accounts table")
    print(f"   Looking for ID: {account_id}")

# Check if chart_of_accounts table exists
result = conn.execute(
    text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'chart_of_accounts')"
    )
)
chart_table_exists = result.fetchone()[0]

if chart_table_exists:
    print("\n⚠️  chart_of_accounts table EXISTS (this might be the issue!)")
    result = conn.execute(
        text(
            f"SELECT id, account_code, account_name FROM chart_of_accounts WHERE id = '{account_id}'"
        )
    )
    row = result.fetchone()
    if row:
        print(f"   Account found in chart_of_accounts: {row[1]} - {row[2]}")
    else:
        print("   Account NOT in chart_of_accounts either")
else:
    print("\n✅ chart_of_accounts table does NOT exist (correct)")

# Show the foreign key constraint
print("\nForeign key constraint on journal_entry_lines:")
result = conn.execute(
    text("""
    SELECT 
        tc.constraint_name,
        kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
    WHERE tc.table_name = 'journal_entry_lines'
        AND tc.constraint_type = 'FOREIGN KEY'
        AND kcu.column_name = 'account_id'
""")
)

for row in result.fetchall():
    print(f"   Constraint: {row[0]}")
    print(f"   Column: {row[1]}")
    print(f"   References: {row[2]}.{row[3]}")
