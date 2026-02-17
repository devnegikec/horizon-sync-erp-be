"""add account_audit_log table

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = 'd4e5f6g7h8i9'
down_revision = 'c3d4e5f6g7h8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create account_audit_log table"""
    op.create_table(
        'account_audit_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('account_id', UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('changes', JSONB, nullable=False),
        sa.Column('audit_metadata', JSONB, nullable=True),
        sa.CheckConstraint(
            "action IN ('CREATE', 'UPDATE', 'DELETE', 'STATUS_CHANGE')",
            name='valid_action'
        ),
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_audit_account', 'account_audit_log', ['account_id'])
    op.create_index('idx_audit_timestamp', 'account_audit_log', ['timestamp'])
    op.create_index('idx_audit_user', 'account_audit_log', ['user_id'])


def downgrade() -> None:
    """Drop account_audit_log table"""
    op.drop_index('idx_audit_user', table_name='account_audit_log')
    op.drop_index('idx_audit_timestamp', table_name='account_audit_log')
    op.drop_index('idx_audit_account', table_name='account_audit_log')
    op.drop_table('account_audit_log')
