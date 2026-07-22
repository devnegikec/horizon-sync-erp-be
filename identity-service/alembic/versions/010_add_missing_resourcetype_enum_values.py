"""Add missing resourcetype enum values for system admin permissions

Revision ID: 010
Revises: 009
Create Date: 2026-04-10

Adds 'billing', 'reporting', 'customer', 'sales_order', 'invoice', 'supplier',
'purchase_order', 'item', 'item_group', 'warehouse', 'stock_entry', 'batch',
'serial', 'chart_of_account', 'payment', 'setting', 'all', 'invitation'
to the resourcetype PostgreSQL enum so the seed script can insert granular
system_admin permissions.
"""

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None

# Values to add (only those not already in the enum)
NEW_VALUES = [
    "customer",
    "sales_order",
    "invoice",
    "supplier",
    "purchase_order",
    "item",
    "item_group",
    "warehouse",
    "stock_entry",
    "batch",
    "serial",
    "chart_of_account",
    "payment",
    "billing",
    "report",
    "reporting",
    "setting",
    "all",
    "invitation",
    "asn_order",
    "pick_list",
]


def upgrade():
    # Ensure resourcetype enum exists; create it with all values if missing, else add new ones
    alter_stmts = " ".join(
        f"ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS '{val}';"
        for val in NEW_VALUES
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'resourcetype') THEN "
        "CREATE TYPE resourcetype AS ENUM ('user', 'organization', 'team', 'role', 'permission', "
        "'customer', 'sales_order', 'invoice', 'supplier', 'purchase_order', 'item', 'item_group', "
        "'warehouse', 'stock_entry', 'batch', 'serial', 'chart_of_account', 'payment', "
        "'billing', 'report', 'reporting', 'setting', 'all', 'invitation', 'asn_order', 'pick_list'); "
        "ELSE " + alter_stmts + " END IF; END $$;"
    )

    # Ensure actiontype enum exists; create with all values if missing, else add 'invite'
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'actiontype') THEN "
        "CREATE TYPE actiontype AS ENUM ('create', 'read', 'update', 'delete', 'manage', 'execute', 'invite'); "
        "ELSE "
        "ALTER TYPE actiontype ADD VALUE IF NOT EXISTS 'invite'; "
        "END IF; END $$;"
    )


def downgrade():
    # PostgreSQL does not support removing enum values; no-op
    pass
