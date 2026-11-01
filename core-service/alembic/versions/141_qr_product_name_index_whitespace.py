"""Recreate the QR-product name index with full whitespace trimming.

Revision ``140_qr_product_unique_name`` originally built the index on
``lower(btrim(name))``. ``btrim(name)`` only strips ordinary spaces, so names
differing by a trailing tab or newline bypassed the intended
whitespace-normalised uniqueness.

140 already shipped to some databases, so the expression cannot be fixed by
editing it alone. This revision rebuilds the index when the definition differs.

Safety: if rebuilding would surface duplicates that the old index tolerated
(names differing only by tabs/newlines), the migration logs a warning and leaves
the existing index in place rather than failing the deployment. De-duplicate and
re-run to pick up the stricter index.

Revision ID: 141_qr_product_name_index_whitespace
Revises: 140_qr_product_unique_name
Create Date: 2026-11-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_index, has_table

revision: str = "141_qr_product_name_index_whitespace"
down_revision: str | Sequence[str] | None = "140_qr_product_unique_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_qr_products_org_name_ci"

_TRIM_WHITESPACE = "btrim(name, E' \\t\\n\\r\\f\\v')"
_NAME_EXPRESSION = f"lower({_TRIM_WHITESPACE})"

_INDEX_DEFINITION_SQL = sa.text(
    "SELECT indexdef FROM pg_indexes "
    "WHERE schemaname = current_schema() AND indexname = :name"
)

_DUPLICATES_SQL = sa.text(
    f"""
    SELECT organization_id, {_NAME_EXPRESSION} AS name_ci, count(*) AS n
    FROM qr_products
    WHERE deleted_at IS NULL AND name IS NOT NULL AND {_TRIM_WHITESPACE} <> ''
    GROUP BY 1, 2
    HAVING count(*) > 1
    ORDER BY 3 DESC, 2
    """
)


def _current_definition() -> str | None:
    row = op.get_bind().execute(_INDEX_DEFINITION_SQL, {"name": INDEX_NAME}).first()
    return row[0] if row else None


def upgrade() -> None:
    if not has_table("qr_products"):
        return

    definition = _current_definition()
    if definition is not None and "E' " in definition:
        # Already rebuilt with the whitespace-aware expression.
        return

    duplicates = op.get_bind().execute(_DUPLICATES_SQL).fetchall()
    if duplicates:
        preview = "; ".join(
            f"{row[0]} / '{row[1]}' x{row[2]}" for row in duplicates[:10]
        )
        print(
            f"WARNING: keeping the less strict '{INDEX_NAME}' index — "
            f"{len(duplicates)} name group(s) differ only by non-space "
            f"whitespace: {preview}. De-duplicate, then re-run this revision."
        )
        return

    if has_index("qr_products", INDEX_NAME):
        op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        f"{INDEX_NAME} ON qr_products (organization_id, {_NAME_EXPRESSION}) "
        "WHERE deleted_at IS NULL AND name IS NOT NULL "
        f"AND {_TRIM_WHITESPACE} <> ''"
    )


def downgrade() -> None:
    """Restore the spaces-only expression used by revision 140."""
    if not has_table("qr_products"):
        return
    if has_index("qr_products", INDEX_NAME):
        op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        f"{INDEX_NAME} ON qr_products (organization_id, lower(btrim(name))) "
        "WHERE deleted_at IS NULL AND name IS NOT NULL AND btrim(name) <> ''"
    )
