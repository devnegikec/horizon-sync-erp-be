"""add tax and discount fields to invoice_items

Revision ID: 023_tax_discount_invoice
Revises: 022_add_performance_indexes
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '023_tax_discount_invoice'
down_revision = '022_add_performance_indexes'
branch_labels = None
depends_on = None


def upgrade():
    # Add tax and discount columns to invoice_items table
    op.add_column('invoice_items', sa.Column('tax_template_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('invoice_items', sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), server_default='0', nullable=True))
    op.add_column('invoice_items', sa.Column('tax_amount', sa.Numeric(precision=15, scale=2), server_default='0', nullable=True))
    op.add_column('invoice_items', sa.Column('discount_type', sa.String(length=20), server_default='percentage', nullable=True))
    op.add_column('invoice_items', sa.Column('discount_value', sa.Numeric(precision=15, scale=2), server_default='0', nullable=True))
    op.add_column('invoice_items', sa.Column('discount_amount', sa.Numeric(precision=15, scale=2), server_default='0', nullable=True))
    op.add_column('invoice_items', sa.Column('total_amount', sa.Numeric(precision=15, scale=2), server_default='0', nullable=True))
    
    # Add foreign key constraint for tax_template_id
    op.create_foreign_key(
        'fk_invoice_items_tax_template_id',
        'invoice_items',
        'tax_templates',
        ['tax_template_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    # Drop foreign key constraint
    op.drop_constraint('fk_invoice_items_tax_template_id', 'invoice_items', type_='foreignkey')
    
    # Drop columns
    op.drop_column('invoice_items', 'total_amount')
    op.drop_column('invoice_items', 'discount_amount')
    op.drop_column('invoice_items', 'discount_value')
    op.drop_column('invoice_items', 'discount_type')
    op.drop_column('invoice_items', 'tax_amount')
    op.drop_column('invoice_items', 'tax_rate')
    op.drop_column('invoice_items', 'tax_template_id')
