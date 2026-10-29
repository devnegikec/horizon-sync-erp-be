"""Enforce case-insensitive unique active serial prefixes per organization.

Serial prefixes are normalized to uppercase by the service, while the index
also trims and lowercases values so legacy rows and direct database writes are
covered by the same uniqueness rule.

Revision ID: 141_qr_serial_prefix_unique
Revises: 140_qr_product_unique_name
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_index, has_table

revision: str = "141_qr_serial_prefix_unique"
down_revision: str | Sequence[str] | None = "140_qr_product_unique_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_qr_prod_settings_org_serial_prefix_ci"

_DUPLICATES_SQL = sa.text(
    """
    SELECT organization_id, lower(btrim(value)) AS prefix_ci, count(*) AS n
    FROM qr_product_settings
    WHERE deleted_at IS NULL
      AND setting_type = 'serial_prefix'
      AND value IS NOT NULL
      AND btrim(value) <> ''
    GROUP BY 1, 2
    HAVING count(*) > 1
    ORDER BY 3 DESC, 2
    """
)


def upgrade() -> None:
    if not has_table("qr_product_settings") or has_index("qr_product_settings", INDEX_NAME):
        return

    duplicates = op.get_bind().execute(_DUPLICATES_SQL).fetchall()
    if duplicates:
        preview = "; ".join(
            f"{row[0]} / '{row[1]}' x{row[2]}" for row in duplicates[:10]
        )
        raise RuntimeError(
            f"Cannot create unique index '{INDEX_NAME}': {len(duplicates)} "
            f"serial-prefix group(s) are duplicated within an organization — "
            f"{preview}. Resolve the duplicates, then re-run the migration."
        )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        f"{INDEX_NAME} ON qr_product_settings "
        "(organization_id, lower(btrim(value))) "
        "WHERE setting_type = 'serial_prefix' "
        "AND deleted_at IS NULL "
        "AND value IS NOT NULL "
        "AND btrim(value) <> ''"
    )


def downgrade() -> None:
    if has_table("qr_product_settings") and has_index("qr_product_settings", INDEX_NAME):
        op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
