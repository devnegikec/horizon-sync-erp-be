#!/usr/bin/env python3
"""
Script to update existing accounts with proper default values for level, is_group, and status
"""

import os
import sys

import psycopg2
from psycopg2.extras import RealDictCursor


def update_account_defaults():
    """Update accounts with proper default values"""

    # Database configuration - using environment variables or defaults
    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "database": os.getenv("DB_NAME", "horizon_sync_core"),
        "user": os.getenv("DB_USER", "horizon_sync"),
        "password": os.getenv("DB_PASSWORD", "GdpdITEseg!2024"),
    }

    try:
        # Connect to database
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        print("Connected to database successfully")

        # First, check which columns exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'accounts' 
            AND column_name IN ('level', 'is_group', 'status')
        """)
        existing_cols = [row["column_name"] for row in cursor.fetchall()]
        print(f"Existing columns: {existing_cols}")

        # Add missing columns if they don't exist
        if "level" not in existing_cols:
            cursor.execute(
                "ALTER TABLE accounts ADD COLUMN level INTEGER NOT NULL DEFAULT 1"
            )
            print("Added level column")

        if "is_group" not in existing_cols:
            cursor.execute(
                "ALTER TABLE accounts ADD COLUMN is_group BOOLEAN NOT NULL DEFAULT false"
            )
            print("Added is_group column")

        # Update any NULL status values to ACTIVE
        cursor.execute("""
            UPDATE accounts 
            SET status = 'ACTIVE' 
            WHERE status IS NULL OR status = ''
        """)
        status_updated = cursor.rowcount
        print(f"Updated {status_updated} accounts with NULL/empty status to ACTIVE")

        # Update level based on parent hierarchy
        cursor.execute("""
            WITH RECURSIVE account_hierarchy AS (
                -- Root accounts (no parent)
                SELECT id, parent_account_id, 1 as level_calc
                FROM accounts 
                WHERE parent_account_id IS NULL
                
                UNION ALL
                
                -- Child accounts
                SELECT a.id, a.parent_account_id, ah.level_calc + 1
                FROM accounts a
                INNER JOIN account_hierarchy ah ON a.parent_account_id = ah.id
            )
            UPDATE accounts 
            SET level = ah.level_calc
            FROM account_hierarchy ah
            WHERE accounts.id = ah.id 
            AND accounts.level != ah.level_calc
        """)
        level_updated = cursor.rowcount
        print(f"Updated levels for {level_updated} accounts based on hierarchy")

        # Update is_group for accounts that have children
        cursor.execute("""
            UPDATE accounts 
            SET is_group = true 
            WHERE id IN (
                SELECT DISTINCT parent_account_id 
                FROM accounts 
                WHERE parent_account_id IS NOT NULL
            )
            AND is_group = false
        """)
        group_updated = cursor.rowcount
        print(
            f"Updated {group_updated} accounts to is_group = true (accounts with children)"
        )

        # Get final count of accounts
        cursor.execute("SELECT COUNT(*) as total FROM accounts")
        total_accounts = cursor.fetchone()["total"]

        print("\\nSummary:")
        print(f"- Total accounts: {total_accounts}")
        print(f"- Status updates: {status_updated}")
        print(f"- Level updates: {level_updated}")
        print(f"- Group flag updates: {group_updated}")

        # Commit changes
        conn.commit()
        print("\\nAll changes committed successfully!")

    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
        return False

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("Database connection closed")

    return True


if __name__ == "__main__":
    success = update_account_defaults()
    if success:
        print("Account defaults updated successfully!")
        sys.exit(0)
    else:
        print("Failed to update account defaults")
        sys.exit(1)
