"""add uoms and uom_conversions tables

Revision ID: m3n4o5p6q7r8s9
Revises: l2m3n4o5p6q7r8
Create Date: 2026-02-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'm3n4o5p6q7r8s9'
down_revision = 'l2m3n4o5p6q7r8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create uoms table
    op.create_table(
        'uoms',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('abbreviation', sa.String(10), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_uoms_org_id', 'uoms', ['organization_id'])
    op.create_index('ix_uoms_organization_id', 'uoms', ['organization_id'])
    op.create_index(
        'uq_uom_org_name', 'uoms', ['organization_id', 'name'],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        'uq_uom_org_abbr', 'uoms', ['organization_id', 'abbreviation'],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Create uom_conversions table
    op.create_table(
        'uom_conversions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('from_uom', sa.String(50), nullable=False),
        sa.Column('to_uom', sa.String(50), nullable=False),
        sa.Column('conversion_factor', sa.Numeric(19, 6), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('conversion_factor > 0', name='ck_uom_conv_positive_factor'),
    )
    op.create_index('ix_uom_conversions_organization_id', 'uom_conversions', ['organization_id'])
    op.create_index('ix_uom_conversions_item', 'uom_conversions', ['item_id'])
    op.create_index(
        'uq_uom_conv_org_item_pair',
        'uom_conversions',
        ['organization_id', 'item_id', 'from_uom', 'to_uom'],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index('uq_uom_conv_org_item_pair', 'uom_conversions')
    op.drop_index('ix_uom_conversions_item', 'uom_conversions')
    op.drop_index('ix_uom_conversions_organization_id', 'uom_conversions')
    op.drop_table('uom_conversions')

    op.drop_index('uq_uom_org_abbr', 'uoms')
    op.drop_index('uq_uom_org_name', 'uoms')
    op.drop_index('ix_uoms_organization_id', 'uoms')
    op.drop_index('ix_uoms_org_id', 'uoms')
    op.drop_table('uoms')
