"""Add bank_accounts table for banking integration

Revision ID: 017_add_bank_accounts_table
Revises: 016_merge_heads
Create Date: 2026-02-27 14:30:00.000000

This migration adds the bank_accounts table to support multiple banking accounts
per GL account with clean separation of concerns.

Tables created:
- bank_accounts (banking information with encrypted sensitive fields)
- bank_account_history (audit trail for banking changes)
"""

from alembic import op  
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "017_add_bank_accounts_table"
down_revision = "001_merged_complete_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get the current connection and inspect existing tables
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # --- Create bank_accounts table ---
    if 'bank_accounts' not in existing_tables:
        op.create_table(
            'bank_accounts',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column('gl_account_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
            
            # Banking information
            sa.Column('bank_name', sa.String(100), nullable=False),
            sa.Column('account_holder_name', sa.String(200), nullable=False),
            sa.Column('account_number', sa.String(50), nullable=False),
            sa.Column('iban', sa.String(34), nullable=True),
            sa.Column('swift_code', sa.String(11), nullable=True),
            sa.Column('routing_number', sa.String(20), nullable=True),
            sa.Column('branch_name', sa.String(100), nullable=True),
            sa.Column('branch_code', sa.String(20), nullable=True),
            sa.Column('sort_code', sa.String(10), nullable=True),
            sa.Column('bsb_number', sa.String(10), nullable=True),
            
            # Account metadata
            sa.Column('account_type', sa.String(50), nullable=True),
            sa.Column('account_purpose', sa.String(50), nullable=True),
            sa.Column('is_primary', sa.Boolean(), nullable=False, default=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
            
            # Banking features
            sa.Column('online_banking_enabled', sa.Boolean(), default=False),
            sa.Column('mobile_banking_enabled', sa.Boolean(), default=False),
            sa.Column('wire_transfer_enabled', sa.Boolean(), default=False),
            sa.Column('ach_enabled', sa.Boolean(), default=False),
            
            # Limits and controls
            sa.Column('daily_transfer_limit', sa.Numeric(15, 2), nullable=True),
            sa.Column('monthly_transfer_limit', sa.Numeric(15, 2), nullable=True),
            sa.Column('requires_dual_approval', sa.Boolean(), default=False),
            
            # Integration settings  
            sa.Column('bank_api_enabled', sa.Boolean(), default=False),
            sa.Column('bank_api_credentials_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('last_sync_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('sync_frequency', sa.String(20), default='manual'),
            
            # Audit fields
            sa.Column('created_by', sa.String(100), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_by', sa.String(100), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            
            sa.ForeignKeyConstraint(['gl_account_id'], ['accounts.id'], name='fk_bank_accounts_gl_account', ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id', name='pk_bank_accounts')
        )
        
        # Unique constraints and indexes only if table was just created
        op.create_unique_constraint('unique_iban_per_org', 'bank_accounts', ['organization_id', 'iban'])
        op.create_index('idx_bank_accounts_gl_account', 'bank_accounts', ['gl_account_id'])
        op.create_index('idx_bank_accounts_org', 'bank_accounts', ['organization_id'])
        op.create_index('idx_bank_accounts_iban', 'bank_accounts', ['iban'], postgresql_where=sa.text('iban IS NOT NULL'))
        op.create_index('idx_bank_accounts_active', 'bank_accounts', ['is_active'], postgresql_where=sa.text('is_active = TRUE'))
        op.create_index('idx_bank_accounts_primary', 'bank_accounts', ['is_primary'], postgresql_where=sa.text('is_primary = TRUE'))

    # --- Create bank_account_history table ---
    if 'bank_account_history' not in existing_tables:
        op.create_table(
            'bank_account_history',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('bank_account_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('action_type', sa.String(50), nullable=False),
            sa.Column('old_values', postgresql.JSONB(), nullable=True),
            sa.Column('new_values', postgresql.JSONB(), nullable=True),  
            sa.Column('changed_by', sa.String(100), nullable=False),
            sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('reason', sa.Text(), nullable=True),
            
            sa.ForeignKeyConstraint(['bank_account_id'], ['bank_accounts.id'], name='fk_bank_account_history_bank_account'),
            sa.PrimaryKeyConstraint('id', name='pk_bank_account_history')
        )
        op.create_index('idx_bank_account_history_bank_account', 'bank_account_history', ['bank_account_id'])
        op.create_index('idx_bank_account_history_action_type', 'bank_account_history', ['action_type'])

def downgrade() -> None:
    # Conditional drop
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if 'bank_account_history' in existing_tables:
        op.drop_table('bank_account_history')
    
    if 'bank_accounts' in existing_tables:
        op.drop_table('bank_accounts')