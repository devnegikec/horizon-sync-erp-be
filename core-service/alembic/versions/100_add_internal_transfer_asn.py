"""Add internal-transfer fields to ASN orders + serialized unit lines.

Revision ID: 100
Revises: 099_add_task_accept_and_worker_sessions
Create Date: 2026-08-31

Adds support for Inter-Warehouse Stock Transfer (IWT) ASNs:
- ``asn_orders.asn_type``  (``purchase`` | ``internal_transfer``)
- ``asn_order_items.serial_nos`` / ``shipped_qty`` / ``received_qty``
- new ``asn_order_serial_lines`` table for unit-level serial tracking

All statements are idempotent (``IF NOT EXISTS``) so the migration is safe
against the project's multi-head ``alembic upgrade heads`` bootstrap.
"""

from alembic import op

revision = "100_add_internal_transfer_asn"
down_revision = "099_add_task_accept_and_worker_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE asn_orders ADD COLUMN IF NOT EXISTS asn_type VARCHAR(20)")

    op.execute(
        "ALTER TABLE asn_order_items ADD COLUMN IF NOT EXISTS serial_nos JSONB"
    )
    op.execute(
        "ALTER TABLE asn_order_items "
        "ADD COLUMN IF NOT EXISTS shipped_qty NUMERIC(15, 3) DEFAULT 0 NOT NULL"
    )
    op.execute(
        "ALTER TABLE asn_order_items "
        "ADD COLUMN IF NOT EXISTS received_qty NUMERIC(15, 3) DEFAULT 0 NOT NULL"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS asn_order_serial_lines (
            id UUID PRIMARY KEY,
            organization_id UUID NOT NULL,
            asn_order_id UUID NOT NULL REFERENCES asn_orders(id) ON DELETE CASCADE,
            asn_item_id UUID REFERENCES asn_order_items(id) ON DELETE CASCADE,
            item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
            serial_no VARCHAR(100) NOT NULL,
            bin_location_id UUID,
            expected_qty INTEGER NOT NULL DEFAULT 1,
            received BOOLEAN NOT NULL DEFAULT false,
            received_at TIMESTAMPTZ,
            received_by UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_asn_order_serial_lines_org "
        "ON asn_order_serial_lines (organization_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_asn_order_serial_lines_asn "
        "ON asn_order_serial_lines (asn_order_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_asn_order_serial_lines_serial "
        "ON asn_order_serial_lines (serial_no)"
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS asn_order_serial_lines")
    op.execute("ALTER TABLE asn_order_items DROP COLUMN IF EXISTS received_qty")
    op.execute("ALTER TABLE asn_order_items DROP COLUMN IF EXISTS shipped_qty")
    op.execute("ALTER TABLE asn_order_items DROP COLUMN IF EXISTS serial_nos")
    op.execute("ALTER TABLE asn_orders DROP COLUMN IF EXISTS asn_type")
