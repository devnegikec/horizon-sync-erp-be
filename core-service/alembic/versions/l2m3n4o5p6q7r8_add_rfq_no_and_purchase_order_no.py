"""add rfq_no and purchase_order_no columns

Revision ID: l2m3n4o5p6q7r8
Revises: k1l2m3n4o5p6q7
Create Date: 2026-02-24

"""
from alembic import op
import sqlalchemy as sa

revision = 'l2m3n4o5p6q7r8'
down_revision = 'k1l2m3n4o5p6q7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('rfqs', sa.Column('rfq_no', sa.String(100), nullable=True))
    op.create_index('ix_rfqs_rfq_no', 'rfqs', ['rfq_no'])

    op.add_column('purchase_orders', sa.Column('purchase_order_no', sa.String(100), nullable=True))
    op.create_index('ix_purchase_orders_purchase_order_no', 'purchase_orders', ['purchase_order_no'])


def downgrade() -> None:
    op.drop_index('ix_purchase_orders_purchase_order_no', 'purchase_orders')
    op.drop_column('purchase_orders', 'purchase_order_no')

    op.drop_index('ix_rfqs_rfq_no', 'rfqs')
    op.drop_column('rfqs', 'rfq_no')
