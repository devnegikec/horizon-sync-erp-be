"""Add performance indexes for default chart of accounts

Revision ID: 022_add_performance_indexes
Revises: 021_create_missing_accounts
Create Date: 2026-03-05

This migration adds performance indexes to optimize queries for the
default chart of accounts setup feature:
- Composite index on accounts(organization_id, account_code) for faster lookups
- Composite index on default_accounts(organization_id, transaction_type) for faster queries

These indexes improve performance when:
1. Looking up accounts by code within an organization
2. Retrieving default account mappings for transaction types
"""

import sqlalchemy as sa
from sqlalchemy import inspect
from alembic import op
from sqlalchemy.engine.reflection import Inspector

revision = "022_add_performance_indexes"
down_revision = "021_create_missing_accounts"
branch_labels = None
depends_on = None


def _existing_indexes(conn, table_name):
    """Get existing indexes for a table"""
    inspector = Inspector.from_engine(conn)
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    """Add performance indexes"""
    conn = op.get_bind()

    # Check if accounts table exists
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    if "accounts" in tables:
        existing_indexes = _existing_indexes(conn, "accounts")

        # Add composite index on accounts(organization_id, account_code)
        # This index already exists from migration 021, but we check to be safe
        if "idx_accounts_org_code" not in existing_indexes:
            op.create_index(
                "idx_accounts_org_code",
                "accounts",
                ["organization_id", "account_code"],
            )
            print("✅ Created index: idx_accounts_org_code")
        else:
            print("ℹ️  Index idx_accounts_org_code already exists")

    if "default_accounts" in tables:
        existing_indexes = _existing_indexes(conn, "default_accounts")

        # Add composite index on default_accounts(organization_id, transaction_type)
        if "idx_default_accounts_org_transaction_type" not in existing_indexes:
            op.create_index(
                "idx_default_accounts_org_transaction_type",
                "default_accounts",
                ["organization_id", "transaction_type"],
            )
            print("✅ Created index: idx_default_accounts_org_transaction_type")
        else:
            print("ℹ️  Index idx_default_accounts_org_transaction_type already exists")

    print("✅ Migration 022: Performance indexes added successfully")


def downgrade() -> None:
    """Remove performance indexes"""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    if "default_accounts" in tables:
        existing_indexes = _existing_indexes(conn, "default_accounts")
        if "idx_default_accounts_org_transaction_type" in existing_indexes:
            op.drop_index(
                "idx_default_accounts_org_transaction_type",
                table_name="default_accounts",
            )
            print("✅ Dropped index: idx_default_accounts_org_transaction_type")

    # Note: We don't drop idx_accounts_org_code as it was created in migration 021
    # and may be relied upon by other parts of the system

    print("✅ Migration 022: Performance indexes removed successfully")
