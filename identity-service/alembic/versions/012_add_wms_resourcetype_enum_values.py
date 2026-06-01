"""Add WMS resourcetype enum values for pick_list and asn_order

Revision ID: 012
Revises: 011
Create Date: 2026-06-01

Adds 'asn_order' and 'pick_list' to the resourcetype PostgreSQL enum
so WMS permissions can be inserted.
"""
from alembic import op


revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'asn_order'")
    op.execute("ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'pick_list'")


def downgrade():
    # PostgreSQL does not support removing enum values; no-op
    pass
