"""Add bank_account_id to payment_entries table

Revision ID: 020_add_bank_account_id_payment
Revises: 019_add_missing_bank_fields
Create Date: 2026-02-27 17:00:00.000000

This migration adds the bank_account_id field to the payment_entries table
to support tracking which specific bank account was used for Bank_Transfer payments.

Changes:
- Add bank_account_id column (UUID, nullable, foreign key to bank_accounts.id)
- Add index on bank_account_id for query performance
- Set ondelete='SET NULL' to preserve payment records if bank account is deleted
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "020_add_bank_account_id_payment"
down_revision = "019_add_missing_bank_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    # Get the current connection and inspect existing columns
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Check if payment_entries table exists
    existing_tables = inspector.get_table_names()
    if 'payment_entries' not in existing_tables:
        # Table doesn't exist, skip this migration
        return
    
    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('payment_entries')]
    
    # Add bank_account_id if it doesn't exist
    if 'bank_account_id' not in existing_columns:
        # Add the column
        op.add_column('payment_entries', 
            sa.Column('bank_account_id', postgresql.UUID(as_uuid=True), nullable=True)
        )
        
        # Add foreign key constraint
        op.create_foreign_key(
            'fk_payment_entries_bank_account_id',
            'payment_entries',
            'bank_accounts',
            ['bank_account_id'],
            ['id'],
            ondelete='SET NULL'
        )
        
        # Add index for query performance
        op.create_index(
            'ix_payment_entries_bank_account_id',
            'payment_entries',
            ['bank_account_id']
        )


def downgrade() -> None:
    # Get the current connection and inspect existing columns
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Check if payment_entries table exists
    existing_tables = inspector.get_table_names()
    if 'payment_entries' not in existing_tables:
        return
    
    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('payment_entries')]
    
    # Drop index, foreign key, and column if they exist
    if 'bank_account_id' in existing_columns:
        # Drop index
        op.drop_index('ix_payment_entries_bank_account_id', table_name='payment_entries')
        
        # Drop foreign key constraint
        op.drop_constraint('fk_payment_entries_bank_account_id', 'payment_entries', type_='foreignkey')
        
        # Drop column
        op.drop_column('payment_entries', 'bank_account_id')
