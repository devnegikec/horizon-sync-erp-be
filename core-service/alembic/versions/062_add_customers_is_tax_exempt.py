"""Add is_tax_exempt column to customers table

Revision ID: 062
Revises: 048_merge_multiple_heads
Create Date: 2026-07-22
"""


from alembic import op

revision = "062"
down_revision = "048_merge_multiple_heads"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name='customers' AND column_name='is_tax_exempt') THEN "
        "ALTER TABLE customers ADD COLUMN is_tax_exempt BOOLEAN DEFAULT FALSE; "
        "END IF; END $$;"
    )


def downgrade():
    pass
