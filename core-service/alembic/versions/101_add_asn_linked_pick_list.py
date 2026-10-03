"""Add linked_pick_list_id to ASN orders (transfer fulfilment visibility).

Revision ID: 101
Revises: 100_add_internal_transfer_asn
Create Date: 2026-08-31

Tracks the source pick list auto-created for an internal-transfer ASN so the
creation side (destination warehouse) can see that fulfilment has started.
"""

from alembic import op

revision = "101_add_asn_linked_pick_list"
down_revision = "100_add_internal_transfer_asn"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE asn_orders ADD COLUMN IF NOT EXISTS linked_pick_list_id UUID"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_asn_orders_linked_pick_list "
        "ON asn_orders (linked_pick_list_id)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_asn_orders_linked_pick_list")
    op.execute("ALTER TABLE asn_orders DROP COLUMN IF EXISTS linked_pick_list_id")
