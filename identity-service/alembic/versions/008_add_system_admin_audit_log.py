"""Add system admin audit log table

Create audit log table for tracking system admin actions and administrative
activities across the platform for compliance and security monitoring.

Revision ID: 008
Revises: 007
Create Date: $(date +%Y-%m-%d %H:%M:%S)

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create system admin audit log table.
    
    Create audit logging table to track all system admin actions including:
    1. User role assignments and updates
    2. Access grants and revocations
    3. Organization management actions
    4. System configuration changes
    """
    
    # Create audit action type enum (only if it doesn't exist)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE auditactiontype AS ENUM (
                'assign', 'update', 'revoke', 'access_grant', 'access_revoke'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create system admin audit logs table using raw SQL to avoid enum creation issues
    op.execute("""
        CREATE TABLE IF NOT EXISTS system_admin_audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            action_id VARCHAR(255) NOT NULL,
            action_type auditactiontype NOT NULL,
            admin_user_id UUID NOT NULL,
            admin_username VARCHAR(255) NOT NULL,
            target_user_id UUID,
            target_username VARCHAR(255),
            target_organization_id UUID,
            target_organization_name VARCHAR(255),
            changes_made JSONB NOT NULL DEFAULT '{}',
            performed_by VARCHAR(255) NOT NULL,
            notes VARCHAR(1000),
            performed_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        );
    """)
    
    # Create indexes for efficient querying
    op.create_index(
        'idx_audit_logs_performed_date', 
        'system_admin_audit_logs', 
        ['performed_date']
    )
    
    op.create_index(
        'idx_audit_logs_admin_user', 
        'system_admin_audit_logs', 
        ['admin_user_id', 'performed_date']
    )
    
    op.create_index(
        'idx_audit_logs_target_org', 
        'system_admin_audit_logs', 
        ['target_organization_id', 'performed_date']
    )
    
    op.create_index(
        'idx_audit_logs_action_type', 
        'system_admin_audit_logs', 
        ['action_type', 'performed_date']
    )
    
    # Add table comment for documentation
    op.execute("""
        COMMENT ON TABLE system_admin_audit_logs IS 
        'Audit log for tracking all system admin actions and administrative activities';
    """)


def downgrade():
    """Remove system admin audit log table."""
    
    # Drop table (will automatically drop indexes)
    op.drop_table('system_admin_audit_logs')
    
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS auditactiontype")