"""add payment_audit_log table

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2024-01-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = 'i9j0k1l2m3n4'
down_revision = 'h8i9j0k1l2m3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create payment_audit_log table"""
    
    # Get connection
    connection = op.get_bind()
    
    # Create payment_audit_action enum type if it doesn't exist
    connection.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE payment_audit_action AS ENUM ('CREATE', 'UPDATE', 'CONFIRM', 'CANCEL', 'ALLOCATE', 'DEALLOCATE');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # Create payment_audit_log table
    connection.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS payment_audit_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            payment_id UUID NOT NULL,
            action payment_audit_action NOT NULL,
            user_id UUID NOT NULL,
            old_values JSONB,
            new_values JSONB,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            
            CONSTRAINT fk_payment_audit_log_organization FOREIGN KEY (organization_id) REFERENCES organizations(id),
            CONSTRAINT fk_payment_audit_log_payment FOREIGN KEY (payment_id) REFERENCES payment_entries(id) ON DELETE CASCADE,
            CONSTRAINT fk_payment_audit_log_user FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """))
    
    # Create indexes for payment_audit_log
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_payment_audit_payment_time 
        ON payment_audit_log(payment_id, timestamp)
    """))
    
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_payment_audit_org_time 
        ON payment_audit_log(organization_id, timestamp)
    """))


def downgrade() -> None:
    """Drop payment_audit_log table"""
    
    # Get connection
    connection = op.get_bind()
    
    # Drop indexes
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_payment_audit_org_time"))
    connection.execute(sa.text("DROP INDEX IF EXISTS idx_payment_audit_payment_time"))
    
    # Drop table
    connection.execute(sa.text("DROP TABLE IF EXISTS payment_audit_log"))
    
    # Note: Do NOT drop enum types as they may be used by other tables
