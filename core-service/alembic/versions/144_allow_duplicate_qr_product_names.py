"""Allow duplicate active QR-product names within an organization.

Product names are descriptive labels and are not identity keys. SKU remains
the organization-scoped unique business key through
``uq_qr_products_org_sku_ci``.

Revision ID: 144_allow_duplicate_qr_product_names
Revises: 143_brand_field_lengths
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_index, has_table

revision: str = "144_allow_duplicate_qr_product_names"
down_revision: str | Sequence[str] | None = "143_brand_field_lengths"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_qr_products_org_name_ci"


def upgrade() -> None:
    if has_table("qr_products") and has_index("qr_products", INDEX_NAME):
        op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")


def downgrade() -> None:
    if not has_table("qr_products") or has_index("qr_products", INDEX_NAME):
        return

    duplicates = op.get_bind().execute(
        sa.text(
            """
            SELECT organization_id, lower(btrim(name)) AS name_ci, count(*) AS n
            FROM qr_products
            WHERE deleted_at IS NULL AND name IS NOT NULL AND btrim(name) <> ''
            GROUP BY 1, 2
            HAVING count(*) > 1
            ORDER BY 3 DESC, 2
            """
        )
    ).fetchall()
    if duplicates:
        preview = "; ".join(
            f"{row[0]} / '{row[1]}' x{row[2]}" for row in duplicates[:10]
        )
        raise RuntimeError(
            f"Cannot restore unique index '{INDEX_NAME}': {len(duplicates)} "
            f"duplicate product-name group(s) exist — {preview}."
        )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        f"{INDEX_NAME} ON qr_products (organization_id, lower(btrim(name))) "
        "WHERE deleted_at IS NULL AND name IS NOT NULL AND btrim(name) <> ''"
    )
