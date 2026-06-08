"""Add payment reminder system tables

Task 1D-1: Add reminder_configs and reminder_logs tables for automated
payment reminder management and escalation sequences.

Revision ID: 036
Revises: 035
Create Date: 2026-03-26 14:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect
import uuid

# revision identifiers
revision = '036_add_payment_reminder_system'
down_revision = '035_add_subscription_billing_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Add payment reminder system tables"""
    # Check if tables already exist
    inspector = inspect(op.get_bind())

    # Create reminder_configs table (without custom enum types)
    if not inspector.has_table('reminder_configs'):
        op.create_table('reminder_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False, index=True, unique=True),
        
        # Reminder type and settings (using string instead of enum)
        sa.Column('reminder_type', sa.String(20), nullable=False, server_default='auto'),
        
        # Grace periods and frequencies (in days)
        sa.Column('grace_period_days', sa.Integer, nullable=False, server_default='30'),
        sa.Column('first_reminder_days', sa.Integer, nullable=False, server_default='30'),
        sa.Column('second_reminder_days', sa.Integer, nullable=False, server_default='60'),
        sa.Column('final_notice_days', sa.Integer, nullable=False, server_default='90'),
        sa.Column('auto_deactivate_days', sa.Integer, nullable=False, server_default='120'),
        
        # Reminder frequency settings
        sa.Column('reminder_frequency_days', sa.Integer, nullable=False, server_default='7'),
        sa.Column('max_reminders_per_stage', sa.Integer, nullable=False, server_default='3'),
        
        # Escalation sequence (array of reminder stages)
        sa.Column('escalation_sequence', postgresql.ARRAY(sa.String), nullable=False, 
                 server_default='{"first_reminder", "second_reminder", "final_notice", "deactivation_notice"}'),
        
        # Email template mappings
        sa.Column('first_reminder_template', sa.String(100), nullable=False, server_default='payment_reminder_first'),
        sa.Column('second_reminder_template', sa.String(100), nullable=False, server_default='payment_reminder_second'),
        sa.Column('final_notice_template', sa.String(100), nullable=False, server_default='payment_reminder_final'),
        sa.Column('deactivation_notice_template', sa.String(100), nullable=False, server_default='payment_reminder_deactivation'),
        
        # Settings
        sa.Column('is_enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('auto_deactivate_enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('send_copy_to_admin', sa.Boolean, nullable=False, server_default='true'),
        
        # Additional configuration
        sa.Column('custom_settings', postgresql.JSONB, nullable=True, server_default='{}'),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # Create reminder_logs table (using string instead of enums)
    if not inspector.has_table('reminder_logs'):
        op.create_table('reminder_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('config_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Reminder details (using string instead of enums)
        sa.Column('reminder_stage', sa.String(30), nullable=False),
        sa.Column('reminder_type', sa.String(20), nullable=False),
        
        # Sending details
        sa.Column('recipient_email', sa.String(255), nullable=False),
        sa.Column('recipient_name', sa.String(255), nullable=True),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('template_used', sa.String(100), nullable=True),
        
        # Status and timing (using string instead of enum)
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True),
        
        # Invoice context at time of sending
        sa.Column('invoice_amount', sa.String(20), nullable=True),
        sa.Column('outstanding_amount', sa.String(20), nullable=True),
        sa.Column('days_overdue', sa.Integer, nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        
        # Delivery tracking
        sa.Column('email_response', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('retry_count', sa.Integer, nullable=False, server_default='0'),
        
        # Escalation tracking
        sa.Column('stage_attempt_number', sa.Integer, nullable=False, server_default='1'),
        sa.Column('next_reminder_due', sa.DateTime(timezone=True), nullable=True),
        
        # Additional context
        sa.Column('triggered_by', sa.String(50), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('additional_data', postgresql.JSONB, nullable=True, server_default='{}'),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'))
    )
        
        # Create indexes for performance
        op.create_index('idx_reminder_logs_org_invoice', 'reminder_logs', ['organization_id', 'invoice_id'])
        op.create_index('idx_reminder_logs_status_stage', 'reminder_logs', ['status', 'reminder_stage'])
        op.create_index('idx_reminder_logs_sent_at', 'reminder_logs', ['sent_at'])
        op.create_index('idx_reminder_logs_next_due', 'reminder_logs', ['next_reminder_due'])
        op.create_index('idx_reminder_logs_batch_id', 'reminder_logs', ['batch_id'])
    
    # Create indexes for reminder_configs if table was created
    if not inspector.has_table('reminder_configs'):
        op.create_index('idx_reminder_configs_org_id', 'reminder_configs', ['organization_id'])
    
    
    # Add foreign key constraint within reminder system tables only
    def _has_fk(table_name: str, fk_name: str) -> bool:
        return any(fk['name'] == fk_name for fk in inspector.get_foreign_keys(table_name))

    if not _has_fk('reminder_logs', 'fk_reminder_logs_config'):
        op.create_foreign_key(
            'fk_reminder_logs_config',
            'reminder_logs', 'reminder_configs',
            ['config_id'], ['id'],
            ondelete='SET NULL'
        )

    # Add trigger for updated_at timestamp on reminder_configs
    op.execute("""
        CREATE OR REPLACE FUNCTION update_reminder_config_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trigger_update_reminder_config_updated_at ON reminder_configs;
        CREATE TRIGGER trigger_update_reminder_config_updated_at
            BEFORE UPDATE ON reminder_configs
            FOR EACH ROW
            EXECUTE FUNCTION update_reminder_config_updated_at();
    """)

    # Add trigger for updated_at timestamp on reminder_logs
    op.execute("""
        CREATE OR REPLACE FUNCTION update_reminder_log_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trigger_update_reminder_log_updated_at ON reminder_logs;
        CREATE TRIGGER trigger_update_reminder_log_updated_at
            BEFORE UPDATE ON reminder_logs
            FOR EACH ROW
            EXECUTE FUNCTION update_reminder_log_updated_at();
    """)
    
    # Add table comments for documentation
    op.execute("""
        COMMENT ON TABLE reminder_configs IS 
        'Task 1D-1: Configuration settings for automated payment reminders per organization';
    """)
    
    op.execute("""
        COMMENT ON TABLE reminder_logs IS 
        'Task 1D-1: Audit log of all payment reminder attempts with delivery tracking';
    """)


def downgrade():
    """Remove payment reminder system tables"""
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_update_reminder_config_updated_at ON reminder_configs;")
    op.execute("DROP TRIGGER IF EXISTS trigger_update_reminder_log_updated_at ON reminder_logs;")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS update_reminder_config_updated_at();")
    op.execute("DROP FUNCTION IF EXISTS update_reminder_log_updated_at();")
    
    # Drop foreign key constraints
    op.drop_constraint('fk_reminder_logs_config', 'reminder_logs', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('idx_reminder_logs_batch_id')
    op.drop_index('idx_reminder_logs_next_due')
    op.drop_index('idx_reminder_logs_sent_at')
    op.drop_index('idx_reminder_logs_status_stage')
    op.drop_index('idx_reminder_logs_org_invoice')
    op.drop_index('idx_reminder_configs_org_id')
    
    # Drop tables
    op.drop_table('reminder_logs')
    op.drop_table('reminder_configs')