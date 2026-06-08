"""Add messaging module tables

Revision ID: 027_add_messaging_module
Revises: 026_add_warranty_module
Create Date: 2026-03-20 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = '027_add_messaging_module'
down_revision = '026_add_warranty_module'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── message_templates ─────────────────────────────────────────────────────
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    if not inspector.has_table('message_templates'):
        op.create_table(
        'message_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_name', sa.String(4000), nullable=False),
        # channel: sms | whatsapp | rcs | email
        sa.Column('channel', sa.String(10), nullable=False),
        sa.Column('template_type', sa.String(2), nullable=True),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('template_text', sa.Text, nullable=False),
        sa.Column('media_type', sa.String(3), nullable=True),
        sa.Column('interactive_type', sa.String(3), nullable=True),
        sa.Column('status', sa.String(40), server_default='Not Approved'),
        sa.Column('sender_id', sa.String(6), nullable=True),
        sa.Column('cta_button1', sa.String(20), nullable=True),
        sa.Column('cta_button2', sa.String(20), nullable=True),
        sa.Column('qr_button1', sa.String(20), nullable=True),
        sa.Column('qr_button2', sa.String(20), nullable=True),
        sa.Column('qr_button3', sa.String(20), nullable=True),
        sa.Column('entity_name', sa.String(50), nullable=True),
        sa.Column('dlt_principal_entity_id', sa.String(50), nullable=True),
        sa.Column('dlt_template_id', sa.String(50), nullable=True),
        sa.Column('mobtexting_template_id', sa.String(120), nullable=True),
        # service_type: T=transactional, P=promotional
        sa.Column('service_type', sa.String(1), server_default='T'),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    if not _has_index('message_templates', 'idx_msg_templates_org'):
        op.create_index('idx_msg_templates_org', 'message_templates', ['organization_id'])
    if not _has_index('message_templates', 'idx_msg_templates_channel'):
        op.create_index('idx_msg_templates_channel', 'message_templates', ['channel'])

    # ── bulk_message_jobs ─────────────────────────────────────────────────────
    if not inspector.has_table('bulk_message_jobs'):
        op.create_table(
        'bulk_message_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('campaign_tags.id'), nullable=True),
        sa.Column('message_type', sa.String(20), nullable=False),
        sa.Column('sender_id', sa.String(40), nullable=True),
        sa.Column('template_type', sa.String(100), nullable=True),
        sa.Column('media_type', sa.String(100), nullable=True),
        sa.Column('interactive_type', sa.String(100), nullable=True),
        sa.Column('template_name', sa.String(100), nullable=True),
        sa.Column('message_template', sa.Text, nullable=True),
        sa.Column('total_lead', sa.String(400), nullable=True),
        sa.Column('media_link', sa.Text, nullable=True),
        sa.Column('variable', postgresql.JSONB, nullable=True),
        sa.Column('coupon_type', sa.String(256), nullable=True),
        sa.Column('coupon_value', sa.Text, nullable=True),
        sa.Column('start_time', sa.Time, nullable=True),
        sa.Column('end_time', sa.Time, nullable=True),
        sa.Column('template_length', sa.String(30), nullable=True),
        sa.Column('used_credit', sa.String(30), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.Date, server_default=sa.text('CURRENT_DATE')),
    )
    if not _has_index('bulk_message_jobs', 'idx_bulk_jobs_org'):
        op.create_index('idx_bulk_jobs_org', 'bulk_message_jobs', ['organization_id'])
    if not _has_index('bulk_message_jobs', 'idx_bulk_jobs_status'):
        op.create_index('idx_bulk_jobs_status', 'bulk_message_jobs', ['status'])

    # ── scheduled_messages ────────────────────────────────────────────────────
    if not inspector.has_table('scheduled_messages'):
        op.create_table(
        'scheduled_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('campaign_tags.id'), nullable=True),
        sa.Column('message_type', sa.String(20), nullable=False),
        sa.Column('template_name', sa.String(100), nullable=True),
        sa.Column('template_text', sa.String(400), nullable=True),
        sa.Column('variable', postgresql.JSONB, nullable=True),
        sa.Column('sender_id', sa.String(12), nullable=True),
        sa.Column('media_link', sa.Text, nullable=True),
        sa.Column('schedule', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(50), server_default='Pending'),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.Date, server_default=sa.text('CURRENT_DATE')),
    )
    if not _has_index('scheduled_messages', 'idx_scheduled_msgs_org'):
        op.create_index('idx_scheduled_msgs_org', 'scheduled_messages', ['organization_id'])
    if not _has_index('scheduled_messages', 'idx_scheduled_msgs_schedule'):
        op.create_index('idx_scheduled_msgs_schedule', 'scheduled_messages', ['schedule'])

    # ── sms_reports ───────────────────────────────────────────────────────────
    if not inspector.has_table('sms_reports'):
        op.create_table(
        'sms_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('bulk_message_jobs.id'), nullable=True),
        sa.Column('tag', sa.String(50), nullable=True),
        sa.Column('msg_id', sa.String(150), nullable=True),
        sa.Column('sender_id', sa.String(12), nullable=True),
        sa.Column('recipient_number', sa.String(12), nullable=True),
        sa.Column('units', sa.String(50), nullable=True),
        sa.Column('credits', sa.String(250), nullable=True),
        sa.Column('location', sa.String(250), nullable=True),
        sa.Column('region', sa.String(250), nullable=True),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('sent_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deliver_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submit_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.Date, server_default=sa.text('CURRENT_DATE')),
    )
    if not _has_index('sms_reports', 'idx_sms_reports_org'):
        op.create_index('idx_sms_reports_org', 'sms_reports', ['organization_id'])
    if not _has_index('sms_reports', 'idx_sms_reports_recipient'):
        op.create_index('idx_sms_reports_recipient', 'sms_reports', ['recipient_number'])

    # ── whatsapp_reports ──────────────────────────────────────────────────────
    if not inspector.has_table('whatsapp_reports'):
        op.create_table(
        'whatsapp_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('bulk_message_jobs.id'), nullable=True),
        sa.Column('recipient_number', sa.String(12), nullable=True),
        sa.Column('sender_number', sa.String(12), nullable=True),
        sa.Column('operator', sa.String(50), nullable=True),
        sa.Column('circle', sa.String(50), nullable=True),
        sa.Column('conversation_id', sa.String(150), nullable=True),
        sa.Column('template_id', sa.String(150), nullable=True),
        sa.Column('conversation_type', sa.String(250), nullable=True),
        sa.Column('whatsapp_msg_id', sa.String(1000), nullable=True),
        sa.Column('guid', sa.String(250), unique=True, nullable=True),
        sa.Column('tag', sa.String(50), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('reason_code', sa.String(50), nullable=True),
        sa.Column('sent_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deliver_date', sa.DateTime(timezone=True), nullable=True),
    )
    if not _has_index('whatsapp_reports', 'idx_wa_reports_org'):
        op.create_index('idx_wa_reports_org', 'whatsapp_reports', ['organization_id'])
    if not _has_index('whatsapp_reports', 'idx_wa_reports_recipient'):
        op.create_index('idx_wa_reports_recipient', 'whatsapp_reports', ['recipient_number'])

    # ── rcs_credentials ───────────────────────────────────────────────────────
    if not inspector.has_table('rcs_credentials'):
        op.create_table(
        'rcs_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('config', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
    )

    # ── rcs_templates ─────────────────────────────────────────────────────────
    if not inspector.has_table('rcs_templates'):
        op.create_table(
        'rcs_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(256), nullable=True),
        sa.Column('content', postgresql.JSONB, nullable=True),
        sa.Column('status', sa.String(40), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
    )
    if not _has_index('rcs_templates', 'idx_rcs_templates_org'):
        op.create_index('idx_rcs_templates_org', 'rcs_templates', ['organization_id'])

    # ── rcs_reports ───────────────────────────────────────────────────────────
    if not inspector.has_table('rcs_reports'):
        op.create_table(
        'rcs_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('bulk_message_jobs.id'), nullable=True),
        sa.Column('recipient_number', sa.String(12), nullable=True),
        sa.Column('guid', sa.String(250), unique=True, nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('sent_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deliver_date', sa.DateTime(timezone=True), nullable=True),
    )
    if not _has_index('rcs_reports', 'idx_rcs_reports_org'):
        op.create_index('idx_rcs_reports_org', 'rcs_reports', ['organization_id'])

    # ── message_credits ───────────────────────────────────────────────────────
    if not inspector.has_table('message_credits'):
        op.create_table(
        'message_credits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('credit_type', sa.String(50), nullable=False),
        sa.Column('add_credit', sa.Integer, server_default='0'),
        sa.Column('reduce_credit', sa.Integer, server_default='0'),
        sa.Column('balance_credit', sa.Integer, server_default='0'),
        sa.Column('payment_inr', sa.String(250), nullable=True),
        sa.Column('credit_value', sa.String(50), nullable=True),
        sa.Column('payment_detail', sa.String(400), nullable=True),
        sa.Column('transaction_date', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
    )
    if not _has_index('message_credits', 'idx_msg_credits_org'):
        op.create_index('idx_msg_credits_org', 'message_credits', ['organization_id'])


def downgrade() -> None:
    op.drop_table('message_credits')
    op.drop_table('rcs_reports')
    op.drop_table('rcs_templates')
    op.drop_table('rcs_credentials')
    op.drop_table('whatsapp_reports')
    op.drop_table('sms_reports')
    op.drop_table('scheduled_messages')
    op.drop_table('bulk_message_jobs')
    op.drop_table('message_templates')
