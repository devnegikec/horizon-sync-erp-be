"""Add base_currency to organizations

Revision ID: 003
Revises: 002
Create Date: 2024-01-15 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add base_currency column to organizations table"""
    op.add_column(
        "organizations",
        sa.Column("base_currency", sa.String(length=3), nullable=True),
    )
    
    # Set default value for existing organizations
    op.execute("UPDATE organizations SET base_currency = 'USD' WHERE base_currency IS NULL")
    
    # Make the column non-nullable after setting defaults
    op.alter_column("organizations", "base_currency", nullable=False)


def downgrade() -> None:
    """Remove base_currency column from organizations table"""
    op.drop_column("organizations", "base_currency")
