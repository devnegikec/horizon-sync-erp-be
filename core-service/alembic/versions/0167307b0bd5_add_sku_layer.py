"""add_sku_layer

Revision ID: 0167307b0bd5
Revises: a62c68164442
Create Date: 2026-06-24 01:52:23.513451

"""
from collections.abc import Sequence

import sqlalchemy as sa

import app.models.types
from alembic import op

revision: str = '0167307b0bd5'
down_revision: str | None = 'a62c68164442'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── NEW TABLES ─────────────────────────────────────────────────────────────

    op.create_table('variant_attributes',
        sa.Column('id', app.models.types.UUID(), nullable=False),
        sa.Column('organization_id', app.models.types.UUID(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=True),
        sa.Column('created_by', app.models.types.UUID(), nullable=True),
        sa.Column('updated_by', app.models.types.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_variant_attr_org_name')
    )
    op.create_index(op.f('ix_variant_attributes_organization_id'), 'variant_attributes', ['organization_id'], unique=False)

    op.create_table('variant_attribute_values',
        sa.Column('id', app.models.types.UUID(), nullable=False),
        sa.Column('attribute_id', app.models.types.UUID(), nullable=False),
        sa.Column('value', sa.String(length=50), nullable=False),
        sa.Column('display_value', sa.String(length=50), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('created_by', app.models.types.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['attribute_id'], ['variant_attributes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('attribute_id', 'value', name='uq_attr_value')
    )
    op.create_index(op.f('ix_variant_attribute_values_attribute_id'), 'variant_attribute_values', ['attribute_id'], unique=False)

    op.create_table('product_skus',
        sa.Column('id', app.models.types.UUID(), nullable=False),
        sa.Column('organization_id', app.models.types.UUID(), nullable=False),
        sa.Column('product_id', app.models.types.UUID(), nullable=False),
        sa.Column('sku_code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('gtin', sa.String(length=20), nullable=True),
        sa.Column('mrp', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('sr_number_type', sa.String(length=50), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('warranty_period_months', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('extra_data', app.models.types.JSONB(), nullable=True),
        sa.Column('created_by', app.models.types.UUID(), nullable=True),
        sa.Column('updated_by', app.models.types.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['qr_products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_skus_organization_id'), 'product_skus', ['organization_id'], unique=False)
    op.create_index(op.f('ix_product_skus_product_id'), 'product_skus', ['product_id'], unique=False)
    op.create_index(op.f('ix_product_skus_sku_code'), 'product_skus', ['sku_code'], unique=True)

    op.create_table('product_sku_attribute_values',
        sa.Column('id', app.models.types.UUID(), nullable=False),
        sa.Column('sku_id', app.models.types.UUID(), nullable=False),
        sa.Column('attribute_value_id', app.models.types.UUID(), nullable=False),
        sa.Column('created_by', app.models.types.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['attribute_value_id'], ['variant_attribute_values.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sku_id'], ['product_skus.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku_id', 'attribute_value_id', name='uq_sku_attr_value')
    )
    op.create_index(op.f('ix_product_sku_attribute_values_sku_id'), 'product_sku_attribute_values', ['sku_id'], unique=False)
    op.create_index(op.f('ix_product_sku_attribute_values_attribute_value_id'), 'product_sku_attribute_values', ['attribute_value_id'], unique=False)

    # ── NEW COLUMNS on existing tables ─────────────────────────────────────────

    op.add_column('qr_blocks', sa.Column('sku_id', app.models.types.UUID(), nullable=True))
    op.create_index(op.f('ix_qr_blocks_sku_id'), 'qr_blocks', ['sku_id'], unique=False)
    op.create_foreign_key(None, 'qr_blocks', 'product_skus', ['sku_id'], ['id'])

    op.add_column('product_items', sa.Column('sku_id', app.models.types.UUID(), nullable=True))
    op.create_index(op.f('ix_product_items_sku_id'), 'product_items', ['sku_id'], unique=False)
    op.create_foreign_key(None, 'product_items', 'product_skus', ['sku_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint(None, 'product_items', type_='foreignkey')
    op.drop_index(op.f('ix_product_items_sku_id'), table_name='product_items')
    op.drop_column('product_items', 'sku_id')

    op.drop_constraint(None, 'qr_blocks', type_='foreignkey')
    op.drop_index(op.f('ix_qr_blocks_sku_id'), table_name='qr_blocks')
    op.drop_column('qr_blocks', 'sku_id')

    op.drop_index(op.f('ix_product_sku_attribute_values_attribute_value_id'), table_name='product_sku_attribute_values')
    op.drop_index(op.f('ix_product_sku_attribute_values_sku_id'), table_name='product_sku_attribute_values')
    op.drop_table('product_sku_attribute_values')

    op.drop_index(op.f('ix_product_skus_sku_code'), table_name='product_skus')
    op.drop_index(op.f('ix_product_skus_product_id'), table_name='product_skus')
    op.drop_index(op.f('ix_product_skus_organization_id'), table_name='product_skus')
    op.drop_table('product_skus')

    op.drop_index(op.f('ix_variant_attribute_values_attribute_id'), table_name='variant_attribute_values')
    op.drop_table('variant_attribute_values')

    op.drop_index(op.f('ix_variant_attributes_organization_id'), table_name='variant_attributes')
    op.drop_table('variant_attributes')
