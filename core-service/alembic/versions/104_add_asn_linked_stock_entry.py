"""Add linked_stock_entry_id to ASN orders (transfer accounting traceability).

Revision ID: 104
Revises: 103_backfill_asn_type
Create Date: 2026-08-31

Tracks the MATERIAL_TRANSFER stock entry created at dispatch for an
internal-transfer ASN, so the transfer is visible in stock/accounting.
"""

from alembic import op

revision = "104_add_asn_linked_stock_entry"
down_revision = "103_backfill_asn_type"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE asn_orders ADD COLUMN IF NOT EXISTS linked_stock_entry_id UUID"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_asn_orders_linked_stock_entry "
        "ON asn_orders (linked_stock_entry_id)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_asn_orders_linked_stock_entry")
    op.execute("ALTER TABLE asn_orders DROP COLUMN IF EXISTS linked_stock_entry_id")
