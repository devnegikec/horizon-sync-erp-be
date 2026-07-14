"""Add warranty module tables

Revision ID: 026_add_warranty_module
Revises: 025_add_campaigns_coupons_module
Create Date: 2026-03-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '026_add_warranty_module'
down_revision = '025_add_campaigns_coupons_module'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── warranty_periods ──────────────────────────────────────────────────────
    op.create_table(
        'warranty_periods',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('months', sa.Integer, nullable=False),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_default', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
    )
    op.create_index('idx_warranty_periods_org', 'warranty_periods', ['organization_id'])

    # ── warranties ────────────────────────────────────────────────────────────
    op.create_table(
        'warranties',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_item_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('product_items.id'), nullable=True),
        sa.Column('serial_number', sa.String(120), nullable=True),
        sa.Column('customer_name', sa.String(255), nullable=False),
        sa.Column('mobile', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('location', sa.String(120), nullable=True),
        sa.Column('ip', sa.String(120), nullable=True),
        sa.Column('purchase_date', sa.Date, nullable=True),
        sa.Column('warranty_valid_till', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
    )
    op.create_index('idx_warranties_org', 'warranties', ['organization_id'])
    op.create_index('idx_warranties_serial', 'warranties', ['serial_number'])
    op.create_index('idx_warranties_mobile', 'warranties', ['mobile'])


def downgrade() -> None:
    op.drop_table('warranties')
    op.drop_table('warranty_periods')
