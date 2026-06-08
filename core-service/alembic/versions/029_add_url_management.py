"""Add URL management — short_urls table

Revision ID: 029_add_url_management
Revises: 028_add_analytics_module
Create Date: 2026-03-20 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = '029_add_url_management'
down_revision = '028_add_analytics_module'
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    if not inspector.has_table('short_urls'):
        op.create_table(
        'short_urls',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slug', sa.String(20), nullable=False, unique=True),
        sa.Column('original_url', sa.Text, nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        # Optional link to a QR product/item
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('product_item_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('click_count', sa.Integer, server_default='0'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
    )
    if not _has_index('short_urls', 'idx_short_urls_org'):
        op.create_index('idx_short_urls_org', 'short_urls', ['organization_id'])
    if not _has_index('short_urls', 'idx_short_urls_slug'):
        op.create_index('idx_short_urls_slug', 'short_urls', ['slug'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_short_urls_slug', table_name='short_urls')
    op.drop_index('idx_short_urls_org', table_name='short_urls')
    op.drop_table('short_urls')
