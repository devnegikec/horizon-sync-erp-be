"""Merge heads: 015_invoice_party_id and n4o5p6q7r8s9t0

Revision ID: 016_merge_heads
Revises: 015_invoice_party_id, n4o5p6q7r8s9t0
Create Date: 2026-02-26

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "016_merge_heads"
down_revision = ("015_invoice_party_id", "n4o5p6q7r8s9t0")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
