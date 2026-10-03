"""Enforce a unique QR-product SKU per organization (case-insensitive).

A QR product's SKU is the natural business key: it is reused by the linked
inventory Item and is what imports/ASN lines are matched on. Duplicate SKUs
silently split stock and break order/receiving resolution, so the SKU must be
unique within an organization.

Uniqueness is case-insensitive and ignores whitespace; soft-deleted products do
not reserve their SKU. Blank/null SKUs are allowed and are not compared.

Because the index cannot be created while duplicates exist, ``upgrade`` first
reports them and fails with an actionable message instead of half-applying.

Remediation for existing duplicates (keep the earliest row, clear the SKU on the
rest — inspect first, this is a business decision):

    WITH ranked AS (
        SELECT id, row_number() OVER (
            PARTITION BY organization_id, lower(btrim(sku))
            ORDER BY created_at, id
        ) AS rn
        FROM qr_products
        WHERE deleted_at IS NULL AND sku IS NOT NULL AND btrim(sku) <> ''
    )
    SELECT q.id, q.organization_id, q.sku, q.name
    FROM ranked r JOIN qr_products q ON q.id = r.id
    WHERE r.rn > 1;

Revision ID: 134_qr_product_unique_sku
Revises: 133_item_group_default_fields
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_index, has_table

revision: str = "134_qr_product_unique_sku"
down_revision: str | Sequence[str] | None = "133_item_group_default_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_qr_products_org_sku_ci"

_DUPLICATES_SQL = sa.text(
    """
    SELECT organization_id, lower(btrim(sku)) AS sku_ci, count(*) AS n
    FROM qr_products
    WHERE deleted_at IS NULL AND sku IS NOT NULL AND btrim(sku) <> ''
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
            f"{len(duplicates)} SKU group(s) are duplicated within an "
            f"organization — {preview}. De-duplicate first (see the migration "
            "docstring for a remediation query), then re-run the migration."
        )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        f"{INDEX_NAME} ON qr_products (organization_id, lower(btrim(sku))) "
        "WHERE deleted_at IS NULL AND sku IS NOT NULL AND btrim(sku) <> ''"
    )


def downgrade() -> None:
    if has_table("qr_products") and has_index("qr_products", INDEX_NAME):
        op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
