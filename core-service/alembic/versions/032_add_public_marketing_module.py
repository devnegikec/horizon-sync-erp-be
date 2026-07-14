"""Add public/marketing module — public_submissions table

Revision ID: 032_add_public_marketing_module
Revises: 031_add_brand_trust_module
Create Date: 2026-03-20 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision = '032_add_public_marketing_module'
down_revision = '031_add_brand_trust_module'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists
    inspector = inspect(op.get_bind())
    if not inspector.has_table('public_submissions'):
        op.create_table(
            'public_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('submission_type', sa.String(30), nullable=False,
                  comment='contact_us | career | schedule_demo | newsletter | request_callback'),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('mobile', sa.String(20), nullable=True),
        sa.Column('company', sa.String(255), nullable=True),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('payload', postgresql.JSONB, nullable=True,
                  comment='Full form data for type-specific fields'),
        sa.Column('status', sa.String(20), server_default='new',
                  comment='new | acknowledged | processed'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
    )
        op.create_index('idx_pub_submissions_type', 'public_submissions', ['submission_type'])
        op.create_index('idx_pub_submissions_email', 'public_submissions', ['email'])
        op.create_index('idx_pub_submissions_created', 'public_submissions', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_pub_submissions_created', table_name='public_submissions')
    op.drop_index('idx_pub_submissions_email', table_name='public_submissions')
    op.drop_index('idx_pub_submissions_type', table_name='public_submissions')
    op.drop_table('public_submissions')
