"""add journal entry tables

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = 'f6g7h8i9j0k1'
down_revision = 'e5f6g7h8i9j0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create journal_entries and journal_entry_lines tables"""
    
    # Get connection
    connection = op.get_bind()
    
    # Create journalstatus enum type if it doesn't exist
    connection.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE journalstatus AS ENUM ('draft', 'posted', 'cancelled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # Create journal_entries table
    connection.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS journal_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            entry_no VARCHAR(100) NOT NULL,
            posting_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            status journalstatus NOT NULL DEFAULT 'draft',
            voucher_type VARCHAR(50),
            reference_type VARCHAR(50),
            reference_id UUID,
            total_debit NUMERIC(15,2) NOT NULL DEFAULT 0,
            total_credit NUMERIC(15,2) NOT NULL DEFAULT 0,
            remarks TEXT,
            posted_at TIMESTAMP WITH TIME ZONE,
            extra_data JSONB,
            created_by UUID,
            updated_by UUID,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_journal_entries_org_entry_no UNIQUE (organization_id, entry_no)
        )
    """))
    
    # Create journal_entry_lines table
    connection.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS journal_entry_lines (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            journal_entry_id UUID NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
            account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            debit NUMERIC(15,2) NOT NULL DEFAULT 0,
            credit NUMERIC(15,2) NOT NULL DEFAULT 0,
            against_account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
            reference_type VARCHAR(50),
            reference_id UUID,
            remarks TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))
    
    # Create indexes for journal_entries
    connection.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_journal_entries_organization_id ON journal_entries(organization_id)"))
    connection.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_journal_entries_posting_date ON journal_entries(posting_date)"))
    connection.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_journal_entries_status ON journal_entries(status)"))
    connection.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_journal_entries_org_status_date ON journal_entries(organization_id, status, posting_date)"))
    
    # Create indexes for journal_entry_lines
    connection.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_organization_id ON journal_entry_lines(organization_id)"))
    connection.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_journal_entry_id ON journal_entry_lines(journal_entry_id)"))
    connection.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_account_id ON journal_entry_lines(account_id)"))
    connection.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_account_journal ON journal_entry_lines(account_id, journal_entry_id)"))


def downgrade() -> None:
    """Drop journal_entries and journal_entry_lines tables"""
    
    # Get connection
    connection = op.get_bind()
    
    # Drop indexes for journal_entry_lines
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_journal_entry_lines_account_journal"))
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_journal_entry_lines_account_id"))
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_journal_entry_lines_journal_entry_id"))
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_journal_entry_lines_organization_id"))
    
    # Drop indexes for journal_entries
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_journal_entries_org_status_date"))
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_journal_entries_status"))
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_journal_entries_posting_date"))
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_journal_entries_organization_id"))
    
    # Drop tables
    connection.execute(sa.text("DROP TABLE IF EXISTS journal_entry_lines"))
    connection.execute(sa.text("DROP TABLE IF EXISTS journal_entries"))
    
    # Note: Do NOT drop journalstatus enum type as it may be used by other tables
