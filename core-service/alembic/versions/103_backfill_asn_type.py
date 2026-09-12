"""Backfill asn_type='purchase' for legacy ASN orders.

Revision ID: 103
Revises: 102_create_serial_tables
Create Date: 2026-08-31

ASN orders created before the ``asn_type`` column was introduced have a NULL
``asn_type``. The UI's "Purchase ASN" tab filters on ``asn_type='purchase'``,
so those legacy orders disappear. This migration classifies all NULL rows as
purchase (the only other type is ``internal_transfer``).
"""

from alembic import op

revision = "103_backfill_asn_type"
down_revision = "102_create_serial_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE asn_orders SET asn_type = 'purchase' "
        "WHERE asn_type IS NULL"
    )


def downgrade():
    # Setting NULL again would re-hide legacy orders from the purchase tab;
    # this is intentionally a no-op to avoid data loss.
    pass
