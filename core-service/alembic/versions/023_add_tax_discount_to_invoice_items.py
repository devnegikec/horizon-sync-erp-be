"""add tax and discount fields to invoice_items

Revision ID: 023_tax_discount_invoice
Revises: 022_add_performance_indexes
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '023_tax_discount_invoice'
down_revision = '022_add_performance_indexes'
branch_labels = None
depends_on = None


def upgrade():
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    conn = op.get_bind()
    from sqlalchemy.engine.reflection import Inspector
    existing = set(Inspector.from_engine(conn).get_table_names())

    # invoice_items is created by SQLAlchemy create_all at app startup.
    # On a fresh DB it won't exist yet when this migration runs, so skip —
    # the columns will be present from the model definition.
    if 'invoice_items' not in existing:
        return

    # Add tax and discount columns to invoice_items table
    inspector = Inspector.from_engine(conn)
    existing_cols = {c['name'] for c in inspector.get_columns('invoice_items')}

    col_defs = [
        ('tax_template_id', sa.Column('tax_template_id', postgresql.UUID(as_uuid=True), nullable=True)),
        ('tax_rate', sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), server_default='0', nullable=True)),
        ('tax_amount', sa.Column('tax_amount', sa.Numeric(precision=15, scale=2), server_default='0', nullable=True)),
        ('discount_type', sa.Column('discount_type', sa.String(length=20), server_default='percentage', nullable=True)),
        ('discount_value', sa.Column('discount_value', sa.Numeric(precision=15, scale=2), server_default='0', nullable=True)),
        ('discount_amount', sa.Column('discount_amount', sa.Numeric(precision=15, scale=2), server_default='0', nullable=True)),
        ('total_amount', sa.Column('total_amount', sa.Numeric(precision=15, scale=2), server_default='0', nullable=True)),
    ]
    for col_name, col_def in col_defs:
        if col_name not in existing_cols:
            op.add_column('invoice_items', col_def)

    # Add foreign key constraint for tax_template_id only if tax_templates exists
    if 'tax_templates' in existing:
        existing_fks = {fk['name'] for fk in inspector.get_foreign_keys('invoice_items')}
        if 'fk_invoice_items_tax_template_id' not in existing_fks:
            op.create_foreign_key(
                'fk_invoice_items_tax_template_id',
                'invoice_items',
                'tax_templates',
                ['tax_template_id'],
                ['id'],
                ondelete='SET NULL'
            )


def downgrade():
    conn = op.get_bind()
    from sqlalchemy.engine.reflection import Inspector
    existing = set(Inspector.from_engine(conn).get_table_names())

    if 'invoice_items' not in existing:
        return

    inspector = Inspector.from_engine(conn)
    existing_fks = {fk['name'] for fk in inspector.get_foreign_keys('invoice_items')}
    if 'fk_invoice_items_tax_template_id' in existing_fks:
        op.drop_constraint('fk_invoice_items_tax_template_id', 'invoice_items', type_='foreignkey')

    existing_cols = {c['name'] for c in inspector.get_columns('invoice_items')}
    for col in ['total_amount', 'discount_amount', 'discount_value', 'discount_type',
                'tax_amount', 'tax_rate', 'tax_template_id']:
        if col in existing_cols:
            op.drop_column('invoice_items', col)
