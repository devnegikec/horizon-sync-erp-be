"""Add campaigns and coupons module tables

Revision ID: 025_add_campaigns_coupons_module
Revises: 024_add_qr_products_module
Create Date: 2026-03-20 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = '025_add_campaigns_coupons_module'
down_revision = '024_add_qr_products_module'
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    # ── campaigns ─────────────────────────────────────────────────────────────
    if not inspector.has_table('campaigns'):
        if not inspector.has_table('campaigns'):
            op.create_table(
            'campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        # campaign_type: QR, WB (web), etc.
        sa.Column('campaign_type', sa.String(3), nullable=False),
        # campaign_status: A=active, I=inactive
        sa.Column('campaign_status', sa.String(1), server_default='A'),
        sa.Column('location', sa.String(256), nullable=True),
        sa.Column('from_date', sa.Date, nullable=False),
        sa.Column('to_date', sa.Date, nullable=False),
        sa.Column('coupon_deliver', sa.String(50), server_default='Nothing'),
        sa.Column('denominations', sa.Text, nullable=True),
        sa.Column('denominations_value', sa.Text, nullable=True),
        sa.Column('denominations_list', postgresql.JSONB, nullable=True),
        sa.Column('sms_senderid', sa.String(10), nullable=True),
        sa.Column('sms_template', sa.String(256), nullable=True),
        sa.Column('sms_variable', postgresql.JSONB, nullable=True),
        sa.Column('whatsapp_template_name', sa.String(256), nullable=True),
        sa.Column('whatsapp_template_type', sa.String(256), nullable=True),
        sa.Column('whatsapp_media_type', sa.String(256), nullable=True),
        sa.Column('whatsapp_interactive_type', sa.String(256), nullable=True),
        sa.Column('whatsapp_variable', postgresql.JSONB, nullable=True),
        sa.Column('media_link', sa.Text, nullable=True),
        sa.Column('campaign_message', sa.String(256), nullable=True),
        sa.Column('used_message', sa.String(256), nullable=True),
        sa.Column('terms_conditions', sa.Text, nullable=True),
        sa.Column('bypass_url', sa.Text, nullable=True),
        sa.Column('client_url', sa.Text, nullable=True),
        sa.Column('redirect_url_type', sa.String(2), nullable=True),
        sa.Column('budget_cap', sa.Integer, nullable=True),
        sa.Column('scans', sa.Integer, server_default='0'),
        sa.Column('coupon_reissue_time', sa.String(50), nullable=True),
        sa.Column('brand_image_url', sa.Text, nullable=True),
        sa.Column('promotional_image_url', sa.Text, nullable=True),
        sa.Column('congrats_image_url', sa.Text, nullable=True),
        sa.Column('multilink_type', sa.String(3), nullable=True),
        sa.Column('multilink_items', postgresql.JSONB, nullable=True),
        sa.Column('game_config', postgresql.JSONB, nullable=True),
        sa.Column('shuffle', sa.Text, nullable=True),
        sa.Column('shuffle_gb', sa.Text, nullable=True),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        # Audit
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_index('campaigns', 'idx_campaigns_org'):
        op.create_index('idx_campaigns_org', 'campaigns', ['organization_id'])
    if not _has_index('campaigns', 'idx_campaigns_status'):
        op.create_index('idx_campaigns_status', 'campaigns', ['campaign_status'])

    # ── play2win_prizes ───────────────────────────────────────────────────────
    if not inspector.has_table('play2win_prizes'):
        if not inspector.has_table('play2win_prizes'):
            op.create_table(
            'play2win_prizes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('prize_type', sa.String(20), server_default='none'),
        sa.Column('value', sa.Numeric(10, 2), server_default='0'),
        sa.Column('weight', sa.Integer, server_default='1'),
        sa.Column('max_quantity', sa.Integer, nullable=True),
        sa.Column('slot_color', sa.String(7), server_default='#3157EF'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        )
    if not _has_index('play2win_prizes', 'idx_prizes_campaign'):
        op.create_index('idx_prizes_campaign', 'play2win_prizes', ['campaign_id'])

    # ── web_campaigns ─────────────────────────────────────────────────────────
    if not inspector.has_table('web_campaigns'):
        if not inspector.has_table('web_campaigns'):
            op.create_table(
            'web_campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(256), nullable=True),
        sa.Column('campaign_type', sa.String(3), nullable=True),
        sa.Column('campaign_status', sa.String(1), server_default='A'),
        sa.Column('from_date', sa.Date, nullable=True),
        sa.Column('to_date', sa.Date, nullable=True),
        sa.Column('coupon_deliver', sa.String(50), nullable=True),
        sa.Column('denominations', sa.Text, nullable=True),
        sa.Column('terms_conditions', sa.Text, nullable=True),
        sa.Column('config', postgresql.JSONB, nullable=True),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_index('web_campaigns', 'idx_web_campaigns_org'):
        op.create_index('idx_web_campaigns_org', 'web_campaigns', ['organization_id'])

    # ── tags ──────────────────────────────────────────────────────────────────
    if not inspector.has_table('campaign_tags'):
        if not inspector.has_table('campaign_tags'):
            op.create_table(
            'campaign_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('segment', sa.String(20), nullable=True),
        sa.Column('tag_type', sa.String(10), nullable=True),
        sa.Column('tag_source', sa.String(256), nullable=True),
        sa.Column('total_lead', sa.Integer, server_default='0'),
        sa.Column('tag_description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        )
    if not _has_index('campaign_tags', 'idx_campaign_tags_org'):
        op.create_index('idx_campaign_tags_org', 'campaign_tags', ['organization_id'])

    # ── leads ─────────────────────────────────────────────────────────────────
    if not inspector.has_table('campaign_leads'):
        if not inspector.has_table('campaign_leads'):
            op.create_table(
            'campaign_leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('mobilenumber', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('pincode', sa.String(30), nullable=True),
        sa.Column('dob', sa.Date, nullable=True),
        sa.Column('gender', sa.String(30), nullable=True),
        sa.Column('occupation', sa.String(256), nullable=True),
        sa.Column('gst_number', sa.String(256), nullable=True),
        sa.Column('state_name', sa.String(30), nullable=True),
        sa.Column('country', sa.String(30), nullable=True),
        sa.Column('coupon', sa.String(255), nullable=True),
        sa.Column('value', sa.String(255), nullable=True),
        sa.Column('used', sa.String(255), nullable=True),
        sa.Column('expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('used_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rating', sa.String(255), nullable=True),
        sa.Column('comment', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('redeem_mode', sa.String(10), server_default='none'),
        sa.Column('external_lead', sa.Boolean, server_default='false'),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        )
    if not _has_index('campaign_leads', 'idx_leads_org'):
        op.create_index('idx_leads_org', 'campaign_leads', ['organization_id'])
    if not _has_index('campaign_leads', 'idx_leads_mobile'):
        op.create_index('idx_leads_mobile', 'campaign_leads', ['mobilenumber'])
    if not _has_index('campaign_leads', 'idx_leads_campaign'):
        op.create_index('idx_leads_campaign', 'campaign_leads', ['campaign_id'])

    # ── lead_tags (M2M) ───────────────────────────────────────────────────────
    if not inspector.has_table('lead_tags'):
        if not inspector.has_table('lead_tags'):
            op.create_table(
            'lead_tags',
        sa.Column('lead_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('campaign_leads.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('campaign_tags.id', ondelete='CASCADE'),
                  nullable=False),
        sa.PrimaryKeyConstraint('lead_id', 'tag_id'),
        )

    # ── coupons ───────────────────────────────────────────────────────────────
    if not inspector.has_table('coupons'):
        if not inspector.has_table('coupons'):
            op.create_table(
            'coupons',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('web_campaign_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('web_campaigns.id'), nullable=True),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('campaign_leads.id'), nullable=True),
        sa.Column('coupon_code', sa.String(255), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('mobilenumber', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('state_name', sa.String(30), nullable=True),
        sa.Column('dob', sa.Date, nullable=True),
        sa.Column('gender', sa.String(30), nullable=True),
        sa.Column('occupation', sa.String(30), nullable=True),
        sa.Column('units', sa.String(255), server_default='RS'),
        sa.Column('value', sa.String(255), nullable=True),
        sa.Column('used', sa.String(255), nullable=True),
        sa.Column('min_bill_value', sa.String(255), nullable=True),
        sa.Column('expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('used_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('rating', sa.String(255), nullable=True),
        sa.Column('product_rating', sa.String(255), nullable=True),
        sa.Column('color_rating', sa.String(255), nullable=True),
        sa.Column('price_rating', sa.String(255), nullable=True),
        sa.Column('comment', sa.String(255), nullable=True),
        sa.Column('custom_question', postgresql.JSONB, nullable=True),
        sa.Column('custom_answer', postgresql.JSONB, nullable=True),
        sa.Column('acception_id', sa.String(256), nullable=True),
        sa.Column('is_unlocked', sa.Boolean, server_default='false'),
        sa.Column('unlock_count', sa.Integer, server_default='0'),
        sa.Column('final_billed_amount', sa.Float, nullable=True),
        sa.Column('redeem_mode', sa.String(10), server_default='none'),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        )
    if not _has_index('coupons', 'idx_coupons_org'):
        op.create_index('idx_coupons_org', 'coupons', ['organization_id'])
    if not _has_index('coupons', 'idx_coupons_code'):
        op.create_index('idx_coupons_code', 'coupons', ['coupon_code'])
    if not _has_index('coupons', 'idx_coupons_mobile'):
        op.create_index('idx_coupons_mobile', 'coupons', ['mobilenumber'])
    if not _has_index('coupons', 'idx_coupons_campaign'):
        op.create_index('idx_coupons_campaign', 'coupons', ['campaign_id'])

    # ── coupon_unlock_logs ────────────────────────────────────────────────────
    if not inspector.has_table('coupon_unlock_logs'):
        if not inspector.has_table('coupon_unlock_logs'):
            op.create_table(
            'coupon_unlock_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('coupon_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('coupons.id'), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('user_reference', sa.String(255), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        )
    if not _has_index('coupon_unlock_logs', 'idx_coupon_logs_org'):
        op.create_index('idx_coupon_logs_org', 'coupon_unlock_logs', ['organization_id'])
    if not _has_index('coupon_unlock_logs', 'idx_coupon_logs_coupon'):
        op.create_index('idx_coupon_logs_coupon', 'coupon_unlock_logs', ['coupon_id'])

    # ── external_coupons ──────────────────────────────────────────────────────
    if not inspector.has_table('external_coupons'):
        if not inspector.has_table('external_coupons'):
            op.create_table(
            'external_coupons',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('web_campaign_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('web_campaigns.id'), nullable=True),
        sa.Column('coupon_code', sa.String(255), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('mobilenumber', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('state_name', sa.String(30), nullable=True),
        sa.Column('city', sa.String(30), nullable=True),
        sa.Column('zipcode', sa.String(30), nullable=True),
        sa.Column('ip_address', sa.String(255), nullable=True),
        sa.Column('dob', sa.Date, nullable=True),
        sa.Column('age', sa.String(30), nullable=True),
        sa.Column('occupation', sa.String(30), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        )
    if not _has_index('external_coupons', 'idx_ext_coupons_org'):
        op.create_index('idx_ext_coupons_org', 'external_coupons', ['organization_id'])

    # ── coupon_durations ──────────────────────────────────────────────────────
    if not inspector.has_table('coupon_durations'):
        if not inspector.has_table('coupon_durations'):
            op.create_table(
            'coupon_durations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('delivery_type', sa.String(3), nullable=False),
        sa.Column('cooling_periods', sa.Integer, nullable=False),
        sa.Column('min_order_amount', sa.String(256), server_default='1500'),
        )

    # ── shopify_configs ───────────────────────────────────────────────────────
    if not inspector.has_table('shopify_configs'):
        if not inspector.has_table('shopify_configs'):
            op.create_table(
            'shopify_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('api_endpoint', sa.Text, nullable=True),
        sa.Column('auth_token', sa.String(256), nullable=True),
        sa.Column('price_rule_id', sa.String(256), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('shopify_configs')
    op.drop_table('coupon_durations')
    op.drop_table('external_coupons')
    op.drop_table('coupon_unlock_logs')
    op.drop_table('coupons')
    op.drop_table('lead_tags')
    op.drop_table('campaign_leads')
    op.drop_table('campaign_tags')
    op.drop_table('web_campaigns')
    op.drop_table('play2win_prizes')
    op.drop_table('campaigns')
