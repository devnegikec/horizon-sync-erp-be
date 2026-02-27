"""add payment_references table

Revision ID: l2m3n4o5p6q7
Revises: h8i9j0k1l2m3
Create Date: 2024-01-16 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = 'l2m3n4o5p6q7'
down_revision = 'h8i9j0k1l2m3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create payment_references table"""
    
    # Get connection
    connection = op.get_bind()
    
    # Create payment_references table
    connection.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS payment_references (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            payment_id UUID NOT NULL,
            invoice_id UUID NOT NULL,
            allocated_amount NUMERIC(15, 2) NOT NULL,
            exchange_rate NUMERIC(15, 6) DEFAULT 1.0,
            allocated_amount_invoice_currency NUMERIC(15, 2),
            created_by UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            
            CONSTRAINT fk_payment_references_organization FOREIGN KEY (organization_id) REFERENCES organizations(id),
            CONSTRAINT fk_payment_references_payment FOREIGN KEY (payment_id) REFERENCES payment_entries(id) ON DELETE CASCADE,
            CONSTRAINT fk_payment_references_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
            CONSTRAINT fk_payment_references_created_by FOREIGN KEY (created_by) REFERENCES users(id),
            CONSTRAINT check_payment_references_allocated_amount CHECK (allocated_amount > 0),
            CONSTRAINT unique_payment_references_payment_invoice UNIQUE (payment_id, invoice_id)
        )
    """))
    
    # Create indexes for payment_references
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_payment_references_payment 
        ON payment_references(payment_id)
    """))
    
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_payment_references_invoice 
        ON payment_references(invoice_id)
    """))
    
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_payment_references_org 
        ON payment_references(organization_id)
    """))


def downgrade() -> None:
    """Drop payment_references table"""
    
    # Get connection
    connection = op.get_bind()
    
    # Drop indexes
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_payment_references_org"))
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_payment_references_invoice"))
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_payment_references_payment"))
    
    # Drop table
    connection.execute(sa.text("DROP TABLE IF EXISTS payment_references"))
