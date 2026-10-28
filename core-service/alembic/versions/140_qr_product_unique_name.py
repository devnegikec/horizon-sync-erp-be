"""Enforce unique active QR-product names per organization.

Names are compared case-insensitively after trimming whitespace. Soft-deleted
products do not reserve their name. Existing duplicates are reported and must
be resolved before the unique index can be created.

Revision ID: 140_qr_product_unique_name
Revises: 139_repair_qr_scan_event_columns
Create Date: 2026-10-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_index, has_table

revision: str = "140_qr_product_unique_name"
down_revision: str | Sequence[str] | None = "139_repair_qr_scan_event_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_qr_products_org_name_ci"

_DUPLICATES_SQL = sa.text(
    """
    SELECT organization_id, lower(btrim(name)) AS name_ci, count(*) AS n
    FROM qr_products
    WHERE deleted_at IS NULL AND name IS NOT NULL AND btrim(name) <> ''
    GROUP BY 1, 2
    HAVING count(*) > 1
    ORDER BY 3 DESC, 2
    """
)


def upgrade() -> None:
    if not has_table("qr_products") or has_index("qr_products", INDEX_NAME):
        return

    duplicates = op.get_bind().execute(_DUPLICATES_SQL).fetchall()
    if duplicates:
        preview = "; ".join(
            f"{row[0]} / '{row[1]}' x{row[2]}" for row in duplicates[:10]
        )
        raise RuntimeError(
            f"Cannot create unique index '{INDEX_NAME}' on qr_products: "
            f"{len(duplicates)} product-name group(s) are duplicated within "
            f"an organization — {preview}. De-duplicate first, then re-run "
            "the migration."
        )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        f"{INDEX_NAME} ON qr_products (organization_id, lower(btrim(name))) "
        "WHERE deleted_at IS NULL AND name IS NOT NULL AND btrim(name) <> ''"
    )


def downgrade() -> None:
    if has_table("qr_products") and has_index("qr_products", INDEX_NAME):
        op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
