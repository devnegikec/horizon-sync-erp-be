"""Add analytics module — meta_campaigns table

qr_scan_events already created in 024_add_qr_products_module.
This migration adds meta_campaigns for Meta/Facebook ad analytics.

Revision ID: 028_add_analytics_module
Revises: 027_add_messaging_module
Create Date: 2026-03-20 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '028_add_analytics_module'
down_revision = '027_add_messaging_module'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── meta_campaigns ────────────────────────────────────────────────────────
    op.create_table(
        'meta_campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_id', sa.String(256), nullable=True),
        sa.Column('campaign_name', sa.String(256), nullable=True),
        sa.Column('impressions', sa.Integer, nullable=True),
        sa.Column('clicks', sa.Integer, nullable=True),
        sa.Column('spend', sa.Numeric(10, 2), nullable=True),
        sa.Column('reach', sa.Integer, nullable=True),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        sa.Column('fetched_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
    )
    op.create_index('idx_meta_campaigns_org', 'meta_campaigns', ['organization_id'])
    op.create_index('idx_meta_campaigns_campaign_id', 'meta_campaigns', ['campaign_id'])
    op.create_index('idx_meta_campaigns_fetched_at', 'meta_campaigns', ['fetched_at'])


def downgrade() -> None:
    op.drop_index('idx_meta_campaigns_fetched_at', table_name='meta_campaigns')
    op.drop_index('idx_meta_campaigns_campaign_id', table_name='meta_campaigns')
    op.drop_index('idx_meta_campaigns_org', table_name='meta_campaigns')
    op.drop_table('meta_campaigns')
