"""Merge heads: 009 (discount columns) and l2m3n4o5p6q7r8 (rfq/purchase order)

Revision ID: 010_merge
Revises: 009, l2m3n4o5p6q7r8
Create Date: 2026-02-24

Merges two branch heads so 'alembic upgrade head' has a single target.
No schema changes; merge only.
"""

from alembic import op

revision = "010_merge"
down_revision = ("009", "l2m3n4o5p6q7r8")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
