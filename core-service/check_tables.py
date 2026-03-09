"""
Check which tables exist in core_db database.
"""

import os

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)


def check_tables():
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("=" * 80)
        print("TABLES IN core_db DATABASE")
        print("=" * 80)
        print()

        result = conn.execute(
            text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        )

        tables = [row[0] for row in result.fetchall()]

        print(f"Found {len(tables)} tables:\n")
        for table in tables:
            print(f"  • {table}")

        print()
        print("=" * 80)

        # Check specific tables we need for cleanup
        print("\nTables needed for payment cleanup:")
        print("-" * 80)

        needed_tables = [
            "payment_audit_logs",
            "payment_references",
            "payment_entries",
            "journal_entry_lines",
            "journal_entries",
            "invoice_items",
            "invoices",
            "customers",
            "suppliers",
            "document_numbering",
            "default_accounts",
            "accounts",
        ]

        for table in needed_tables:
            exists = table in tables
            status = "✅ EXISTS" if exists else "❌ MISSING"
            print(f"  {status}: {table}")

        print()


if __name__ == "__main__":
    check_tables()
