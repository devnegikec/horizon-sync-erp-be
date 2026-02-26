"""add currency_masters and exchange_rates tables

Revision ID: n4o5p6q7r8s9t0
Revises: m3n4o5p6q7r8s9
Create Date: 2026-02-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'n4o5p6q7r8s9t0'
down_revision = 'm3n4o5p6q7r8s9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'currency_masters' not in tables:
        op.create_table(
            'currency_masters',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('code', sa.String(3), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('symbol', sa.String(5), nullable=True),
            sa.Column('is_base_currency', sa.Boolean, nullable=False, server_default='false'),
            sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index('ix_currency_masters_org_id', 'currency_masters', ['organization_id'])
        op.create_index('ix_currency_masters_organization_id', 'currency_masters', ['organization_id'])
        op.create_index(
            'uq_currency_org_code', 'currency_masters', ['organization_id', 'code'],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )

    if 'exchange_rates' not in tables:
        op.create_table(
            'exchange_rates',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('from_currency', sa.String(3), nullable=False),
            sa.Column('to_currency', sa.String(3), nullable=False),
            sa.Column('rate', sa.Numeric(19, 6), nullable=False),
            sa.Column('effective_date', sa.Date, nullable=False),
            sa.Column('captured_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint('from_currency', 'to_currency', 'effective_date', name='uq_exchange_rate_currency_date'),
            sa.CheckConstraint('rate > 0', name='ck_exchange_rate_positive'),
        )
        op.create_index('ix_exchange_rates_org_id', 'exchange_rates', ['organization_id'])
        op.create_index('ix_exchange_rates_currencies', 'exchange_rates', ['from_currency', 'to_currency'])
        op.create_index('ix_exchange_rates_effective_date', 'exchange_rates', ['effective_date'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'exchange_rates' in tables:
        op.drop_index('ix_exchange_rates_effective_date', 'exchange_rates')
        op.drop_index('ix_exchange_rates_currencies', 'exchange_rates')
        op.drop_index('ix_exchange_rates_org_id', 'exchange_rates')
        op.drop_table('exchange_rates')

    if 'currency_masters' in tables:
        op.drop_index('uq_currency_org_code', 'currency_masters')
        op.drop_index('ix_currency_masters_organization_id', 'currency_masters')
        op.drop_index('ix_currency_masters_org_id', 'currency_masters')
        op.drop_table('currency_masters')
