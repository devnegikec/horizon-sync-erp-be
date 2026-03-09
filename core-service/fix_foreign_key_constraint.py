"""
Fix foreign key constraint on journal_entry_lines to point to accounts table instead of chart_of_accounts.
"""

from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"


def fix_foreign_key():
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("=" * 80)
        print("FIXING FOREIGN KEY CONSTRAINT")
        print("=" * 80)
        print()

        # Step 1: Drop the old foreign key constraint
        print("Step 1: Dropping old foreign key constraint...")
        try:
            conn.execute(
                text("""
                ALTER TABLE journal_entry_lines
                DROP CONSTRAINT IF EXISTS fk_jel_account
            """)
            )
            conn.commit()
            print("  ✓ Dropped fk_jel_account\n")
        except Exception as e:
            print(f"  ⚠ Error: {e}\n")
            conn.rollback()

        # Step 2: Create new foreign key constraint pointing to accounts table
        print("Step 2: Creating new foreign key constraint...")
        try:
            conn.execute(
                text("""
                ALTER TABLE journal_entry_lines
                ADD CONSTRAINT fk_jel_account
                FOREIGN KEY (account_id)
                REFERENCES accounts(id)
                ON DELETE RESTRICT
            """)
            )
            conn.commit()
            print("  ✓ Created fk_jel_account pointing to accounts table\n")
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
            conn.rollback()
            return

        # Step 2b: Drop and recreate fk_jel_against_account
        print("Step 2b: Fixing against_account_id foreign key...")
        try:
            conn.execute(
                text("""
                ALTER TABLE journal_entry_lines
                DROP CONSTRAINT IF EXISTS fk_jel_against_account
            """)
            )
            conn.commit()
            print("  ✓ Dropped fk_jel_against_account")

            conn.execute(
                text("""
                ALTER TABLE journal_entry_lines
                ADD CONSTRAINT fk_jel_against_account
                FOREIGN KEY (against_account_id)
                REFERENCES accounts(id)
                ON DELETE RESTRICT
            """)
            )
            conn.commit()
            print("  ✓ Created fk_jel_against_account pointing to accounts table\n")
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
            conn.rollback()
            return

        # Step 3: Verify the fix
        print("Step 3: Verifying the fix...")
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
            print(f"  Constraint: {row[0]}")
            print(f"  Column: {row[1]}")
            print(f"  References: {row[2]}.{row[3]}")

        print()
        print("=" * 80)
        print("✅ FOREIGN KEY FIXED!")
        print("=" * 80)
        print()
        print("The journal_entry_lines.account_id now correctly references accounts.id")
        print()
        print("Next steps:")
        print("  1. Restart backend server")
        print("  2. Try confirming the payment again")
        print("  3. It should work now!")
        print()


if __name__ == "__main__":
    try:
        fix_foreign_key()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
