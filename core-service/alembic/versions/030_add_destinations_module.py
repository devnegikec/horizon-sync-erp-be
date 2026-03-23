"""Add destinations module — destination_markets table

Revision ID: 030_add_destinations_module
Revises: 029_add_url_management
Create Date: 2026-03-20 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '030_add_destinations_module'
down_revision = '029_add_url_management'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'destination_markets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(20), nullable=False),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('currency_code', sa.String(3), nullable=True,
                  comment='ISO 4217 currency code, links to currency_masters.code'),
        sa.Column('language', sa.String(10), nullable=True,
                  comment='BCP-47 language tag, e.g. en-US'),
        sa.Column('tax_rate', sa.Numeric(5, 4), nullable=True,
                  comment='Default tax rate for this market, e.g. 0.18 for 18%'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_dest_markets_org', 'destination_markets', ['organization_id'])
    op.create_index('idx_dest_markets_code', 'destination_markets', ['organization_id', 'code'],
                    unique=True,
                    postgresql_where=sa.text('deleted_at IS NULL'))


def downgrade() -> None:
    op.drop_index('idx_dest_markets_code', table_name='destination_markets')
    op.drop_index('idx_dest_markets_org', table_name='destination_markets')
    op.drop_table('destination_markets')
