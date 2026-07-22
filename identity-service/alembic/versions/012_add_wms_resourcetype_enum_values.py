"""Add WMS resourcetype enum values for pick_list and asn_order

Revision ID: 012
Revises: 011
Create Date: 2026-06-01

Adds 'asn_order' and 'pick_list' to the resourcetype PostgreSQL enum
so WMS permissions can be inserted.
"""

from alembic import op


revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'resourcetype') THEN "
        "CREATE TYPE resourcetype AS ENUM ('user', 'organization', 'team', 'role', 'permission', "
        "'customer', 'sales_order', 'invoice', 'supplier', 'purchase_order', 'item', 'item_group', "
        "'warehouse', 'stock_entry', 'batch', 'serial', 'chart_of_account', 'payment', "
        "'billing', 'report', 'reporting', 'setting', 'all', 'invitation', 'asn_order', 'pick_list', "
        "'receiving_slip'); "
        "ELSE "
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'asn_order'; "
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'pick_list'; "
        "END IF; END $$;"
    )


def downgrade():
    # PostgreSQL does not support removing enum values; no-op
    pass
