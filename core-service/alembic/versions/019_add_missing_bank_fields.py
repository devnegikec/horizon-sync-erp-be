"""Add missing fields to bank_accounts table

Revision ID: 019_add_missing_bank_fields
Revises: 018_fix_bulk_export_format
Create Date: 2026-02-27 16:00:00.000000

This migration adds missing fields to the bank_accounts table:
- country_code (ISO 3166-1 alpha-2 country code)
- currency (ISO 4217 currency code)
- ifsc_code (Indian Financial System Code for Indian banks)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "019_add_missing_bank_fields"
down_revision = "018_fix_bulk_export_format"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get the current connection and inspect existing columns
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Check if bank_accounts table exists
    existing_tables = inspector.get_table_names()
    if 'bank_accounts' not in existing_tables:
        # Table doesn't exist, skip this migration
        return
    
    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('bank_accounts')]
    
    # Add country_code if it doesn't exist
    if 'country_code' not in existing_columns:
        op.add_column('bank_accounts', 
            sa.Column('country_code', sa.String(2), nullable=True)
        )
        # Set a default value for existing rows
        op.execute("UPDATE bank_accounts SET country_code = 'US' WHERE country_code IS NULL")
        # Make it NOT NULL after setting defaults
        op.alter_column('bank_accounts', 'country_code', nullable=False)
    
    # Add currency if it doesn't exist
    if 'currency' not in existing_columns:
        op.add_column('bank_accounts',
            sa.Column('currency', sa.String(3), nullable=True)
        )
        # Set a default value for existing rows
        op.execute("UPDATE bank_accounts SET currency = 'USD' WHERE currency IS NULL")
        # Make it NOT NULL after setting defaults
        op.alter_column('bank_accounts', 'currency', nullable=False)
    
    # Add ifsc_code if it doesn't exist (for Indian banks)
    if 'ifsc_code' not in existing_columns:
        op.add_column('bank_accounts',
            sa.Column('ifsc_code', sa.String(11), nullable=True)
        )


def downgrade() -> None:
    # Get the current connection and inspect existing columns
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Check if bank_accounts table exists
    existing_tables = inspector.get_table_names()
    if 'bank_accounts' not in existing_tables:
        return
    
    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('bank_accounts')]
    
    # Drop columns if they exist
    if 'ifsc_code' in existing_columns:
        op.drop_column('bank_accounts', 'ifsc_code')
    
    if 'currency' in existing_columns:
        op.drop_column('bank_accounts', 'currency')
    
    if 'country_code' in existing_columns:
        op.drop_column('bank_accounts', 'country_code')
