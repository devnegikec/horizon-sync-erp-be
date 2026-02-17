"""add_exchange_rates_table

Revision ID: a1b2c3d4e5f6
Revises: 8f3a2c1d9b7e
Create Date: 2026-02-17 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "8f3a2c1d9b7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create exchange_rates table
    op.create_table(
        'exchange_rates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('from_currency', sa.String(length=3), nullable=False),
        sa.Column('to_currency', sa.String(length=3), nullable=False),
        sa.Column('rate', sa.Numeric(precision=19, scale=6), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('rate > 0', name='ck_exchange_rate_positive'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('from_currency', 'to_currency', 'effective_date', name='uq_exchange_rate_currency_date')
    )
    
    # Create indexes for currency pairs and effective dates
    op.create_index('ix_exchange_rates_currencies', 'exchange_rates', ['from_currency', 'to_currency'])
    op.create_index('ix_exchange_rates_effective_date', 'exchange_rates', ['effective_date'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_exchange_rates_effective_date', table_name='exchange_rates')
    op.drop_index('ix_exchange_rates_currencies', table_name='exchange_rates')
    
    # Drop table
    op.drop_table('exchange_rates')
