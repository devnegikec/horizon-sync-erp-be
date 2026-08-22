"""add unique constraint on items (organization_id, item_code)

Revision ID: 071_add_unique_constraint_items_org_item_code
Revises: 070_make_tracking_session_columns_nullable
Create Date: 2026-08-13
"""

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_constraint, has_table

# revision identifiers, used by Alembic.
revision = "071_add_unique_constraint_items_org_item_code"
down_revision = "070_make_tracking_session_columns_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add unique constraint if not present
    if has_table("items") and not has_constraint("items", "uq_items_org_item_code"):
        conn = op.get_bind()
        # 1) Create a backup table for duplicates (non-destructive)
        conn.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS items_duplicates_backup (LIKE items INCLUDING ALL);
                """
            )
        )

        # 2) Insert duplicate rows into backup (keep first row per org+item_code)
        conn.execute(
            sa.text(
                """
                INSERT INTO items_duplicates_backup
                SELECT * FROM items
                WHERE id IN (
                  SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (PARTITION BY organization_id, item_code ORDER BY created_at ASC, id ASC) rn
                    FROM items
                  ) t WHERE t.rn > 1
                );
                """
            )
        )

        # 3) Delete duplicate rows, keeping the earliest created row for each (organization_id, item_code)
        conn.execute(
            sa.text(
                """
                WITH ranked AS (
                  SELECT id, ROW_NUMBER() OVER (PARTITION BY organization_id, item_code ORDER BY created_at ASC, id ASC) rn
                  FROM items
                )
                DELETE FROM items WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
                """
            )
        )

        # 4) Finally, add the unique constraint
        op.create_unique_constraint(
            "uq_items_org_item_code",
            "items",
            ["organization_id", "item_code"],
        )


def downgrade() -> None:
    if has_table("items") and has_constraint("items", "uq_items_org_item_code"):
        op.drop_constraint("uq_items_org_item_code", "items", type_="unique")
