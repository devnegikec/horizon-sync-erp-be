"""Add qr_code column to users + warehouse worker enum values

Revision ID: 013
Revises: 012
Create Date: 2026-06-19

- Adds qr_code column to users table (unique, indexed, nullable)
- Adds 'warehouse_worker' to usertype enum
- Adds 'receiving_slip' to resourcetype enum
- Adds 'scan' to actiontype enum
"""

import sqlalchemy as sa

from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add new enum values, guarding against missing types
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'usertype') THEN "
        "CREATE TYPE usertype AS ENUM ('system_admin', 'organization_admin', 'user', 'guest', 'warehouse_worker'); "
        "ELSE "
        "ALTER TYPE usertype ADD VALUE IF NOT EXISTS 'warehouse_worker'; "
        "END IF; END $$;"
    )
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'resourcetype') THEN "
        "CREATE TYPE resourcetype AS ENUM ('user', 'organization', 'team', 'role', 'permission', "
        "'customer', 'sales_order', 'invoice', 'supplier', 'purchase_order', 'item', 'item_group', "
        "'warehouse', 'stock_entry', 'batch', 'serial', 'chart_of_account', 'payment', "
        "'billing', 'report', 'reporting', 'setting', 'all', 'invitation', 'asn_order', 'pick_list', "
        "'receiving_slip'); "
        "ELSE "
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'receiving_slip'; "
        "END IF; END $$;"
    )
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'actiontype') THEN "
        "CREATE TYPE actiontype AS ENUM ('create', 'read', 'update', 'delete', 'manage', 'execute', 'invite', 'scan'); "
        "ELSE "
        "ALTER TYPE actiontype ADD VALUE IF NOT EXISTS 'scan'; "
        "END IF; END $$;"
    )

    # 2. Add qr_code column to users table
    op.add_column(
        "users",
        sa.Column("qr_code", sa.String(100), unique=True, index=True, nullable=True),
    )


def downgrade():
    # Remove qr_code column
    op.drop_index(op.f("ix_users_qr_code"), table_name="users")
    op.drop_column("users", "qr_code")

    # PostgreSQL does not support removing enum values; no-op for enums
