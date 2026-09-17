"""Add QSeal / QR / UOM / Tax resourcetype enum values

Revision ID: 016
Revises: 015
Create Date: 2026-08-12

Adds 'qseal', 'qr_product', 'qr_block', 'landing_page', 'uom', and
'tax_template' to the resourcetype PostgreSQL enum so the
corresponding permissions can be inserted.
"""

from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'qseal'; "
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'qr_product'; "
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'qr_block'; "
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'landing_page'; "
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'uom'; "
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'tax_template';"
    )


def downgrade():
    # PostgreSQL does not support removing enum values; no-op
    pass
