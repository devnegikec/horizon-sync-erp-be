"""Add QR products module tables

Revision ID: 024_add_qr_products_module
Revises: 023_tax_discount_invoice
Create Date: 2026-03-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '024_add_qr_products_module'
down_revision = '023_tax_discount_invoice'
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    # ── qr_products ──────────────────────────────────────────────────────────
    if not inspector.has_table('qr_products'):
        if not inspector.has_table('qr_products'):
            op.create_table(
            'qr_products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('generic_name', sa.String(100), nullable=True),
        sa.Column('gtin', sa.String(20), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('landing_page', sa.Text, nullable=True),
        sa.Column('image_url', sa.Text, nullable=True),
        sa.Column('banner_image_url', sa.Text, nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone_number', sa.String(15), nullable=True),
        sa.Column('client_product_auth_url', sa.Text, nullable=True),
        # pre = pre-activated, post = post-activation
        sa.Column('activation_method', sa.String(4), server_default='pre'),
        sa.Column('sr_number_type', sa.String(12), nullable=True),
        sa.Column('redirect_to_client', sa.Boolean, server_default='false'),
        sa.Column('warranty_period_months', sa.Integer, nullable=True),
        sa.Column('qr_type', sa.String(30), nullable=True),
        sa.Column('is_active', sa.Boolean, server_default='true'),
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
    if not _has_index('qr_products', 'idx_qr_products_org'):
        op.create_index('idx_qr_products_org', 'qr_products', ['organization_id'])

    # ── qr_blocks ─────────────────────────────────────────────────────────────
    if not inspector.has_table('qr_blocks'):
        if not inspector.has_table('qr_blocks'):
            op.create_table(
            'qr_blocks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('qr_products.id'), nullable=False),
        sa.Column('batch', sa.String(50), nullable=False),
        sa.Column('serial_prefix', sa.String(20), nullable=True),
        sa.Column('sr_number', sa.String(256), nullable=True),
        sa.Column('sr_number_type', sa.String(256), nullable=True),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('cert_type', sa.String(1), nullable=True),
        sa.Column('size', sa.String(4), nullable=True),
        sa.Column('colour_desc', sa.String(50), nullable=True),
        sa.Column('price', sa.Integer, nullable=True),
        sa.Column('style', sa.String(20), nullable=True),
        sa.Column('task_status', sa.String(20), nullable=True),
        sa.Column('qr_image', sa.Boolean, server_default='false'),
        sa.Column('manufacture_date', sa.Date, nullable=True),
        sa.Column('expiry_date', sa.Date, nullable=True),
        sa.Column('gcs_url', sa.Text, nullable=True),
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
    if not _has_index('qr_blocks', 'idx_qr_blocks_org'):
        op.create_index('idx_qr_blocks_org', 'qr_blocks', ['organization_id'])
    if not _has_index('qr_blocks', 'idx_qr_blocks_product'):
        op.create_index('idx_qr_blocks_product', 'qr_blocks', ['product_id'])

    # ── product_items ─────────────────────────────────────────────────────────
    if not inspector.has_table('product_items'):
        if not inspector.has_table('product_items'):
            op.create_table(
            'product_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('qr_products.id'), nullable=False),
        sa.Column('block_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('qr_blocks.id'), nullable=True),
        sa.Column('serial_number', sa.String(75), nullable=False),
        sa.Column('secrete_code', sa.String(50), nullable=True),
        sa.Column('token_id', sa.String(75), nullable=True),
        sa.Column('is_unit', sa.Boolean, server_default='false'),
        sa.Column('is_suspicious', sa.Boolean, server_default='false'),
        sa.Column('is_verify', sa.Boolean, server_default='false'),
        sa.Column('is_auth', sa.Boolean, server_default='false'),
        sa.Column('qr_deactive', sa.Boolean, server_default='true'),
        sa.Column('qr_deactive_unit', sa.Boolean, server_default='true'),
        sa.Column('scan_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scans', sa.Integer, server_default='0'),
        sa.Column('destination_market', sa.String(100), nullable=True),
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
    if not _has_index('product_items', 'idx_product_items_org'):
        op.create_index('idx_product_items_org', 'product_items', ['organization_id'])
    if not _has_index('product_items', 'idx_product_items_serial'):
        op.create_index('idx_product_items_serial', 'product_items', ['serial_number'])
    if not _has_index('product_items', 'idx_product_items_product'):
        op.create_index('idx_product_items_product', 'product_items', ['product_id'])

    # ── qr_activation_parameters ──────────────────────────────────────────────
    if not inspector.has_table('qr_activation_parameters'):
        if not inspector.has_table('qr_activation_parameters'):
            op.create_table(
            'qr_activation_parameters',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('qr_products.id'), nullable=True),
        sa.Column('block_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('qr_blocks.id'), nullable=True),
        sa.Column('serial_number', sa.String(75), nullable=True),
        sa.Column('manufacturing_date', sa.Date, nullable=False),
        sa.Column('expiry_date', sa.Date, nullable=False),
        sa.Column('manufacturing_unit', sa.String(100), nullable=False),
        sa.Column('dispatch_batch', sa.String(100), nullable=True),
        sa.Column('destination_market', sa.String(100), nullable=True),
        sa.Column('mrp', sa.Numeric(10, 2), nullable=True),
        sa.Column('currency', sa.String(10), nullable=True),
        sa.Column('batch_size', sa.Integer, nullable=True),
        sa.Column('qr_settings', sa.Boolean, server_default='false'),
        sa.Column('qr_cascade', sa.Boolean, server_default='false'),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        )
    if not _has_index('qr_activation_parameters', 'idx_qr_act_params_org'):
        op.create_index('idx_qr_act_params_org', 'qr_activation_parameters',
                        ['organization_id'])

    # ── qr_activation_tracks ──────────────────────────────────────────────────
    if not inspector.has_table('qr_activation_tracks'):
        if not inspector.has_table('qr_activation_tracks'):
            op.create_table(
            'qr_activation_tracks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('qr_type', sa.String(25), nullable=True),
        sa.Column('name', sa.String(20), nullable=True),
        sa.Column('capacity', sa.Integer, nullable=True),
        sa.Column('serial_number', sa.String(10), nullable=True),
        sa.Column('qr_code_link', sa.Text, nullable=True),
        sa.Column('app_cascade_map', sa.Boolean, server_default='false'),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('qr_activation_tracks.id'), nullable=True),
        sa.Column('parent_app_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('qr_activation_tracks.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        )
    if not _has_index('qr_activation_tracks', 'idx_qr_act_tracks_org'):
        op.create_index('idx_qr_act_tracks_org', 'qr_activation_tracks',
                        ['organization_id'])

    # ── qr_credit_usage ───────────────────────────────────────────────────────
    if not inspector.has_table('qr_credit_usage'):
        if not inspector.has_table('qr_credit_usage'):
            op.create_table(
            'qr_credit_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('block_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('qr_blocks.id'), nullable=True),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        )
    if not _has_index('qr_credit_usage', 'idx_qr_credit_org'):
        op.create_index('idx_qr_credit_org', 'qr_credit_usage', ['organization_id'])

    # ── qr_scan_events ────────────────────────────────────────────────────────
    if not inspector.has_table('qr_scan_events'):
        if not inspector.has_table('qr_scan_events'):
            op.create_table(
            'qr_scan_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_item_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('product_items.id'), nullable=True),
        sa.Column('serial_number', sa.String(75), nullable=True),
        sa.Column('scan_timestamp', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('os', sa.String(50), nullable=True),
        sa.Column('browser', sa.String(50), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('latitude', sa.Numeric(9, 6), nullable=True),
        sa.Column('longitude', sa.Numeric(9, 6), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        )
    if not _has_index('qr_scan_events', 'idx_qr_scan_org'):
        op.create_index('idx_qr_scan_org', 'qr_scan_events', ['organization_id'])
    if not _has_index('qr_scan_events', 'idx_qr_scan_serial'):
        op.create_index('idx_qr_scan_serial', 'qr_scan_events', ['serial_number'])
    if not _has_index('qr_scan_events', 'idx_qr_scan_ts'):
        op.create_index('idx_qr_scan_ts', 'qr_scan_events', ['scan_timestamp'])


def downgrade() -> None:
    op.drop_table('qr_scan_events')
    op.drop_table('qr_credit_usage')
    op.drop_table('qr_activation_tracks')
    op.drop_table('qr_activation_parameters')
    op.drop_table('product_items')
    op.drop_table('qr_blocks')
    op.drop_table('qr_products')
