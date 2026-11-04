"""Rebuild the QR-product name index with a correct vertical-tab trim.

Revisions ``140_qr_product_unique_name`` and ``141_qr_product_name_index_whitespace``
both built the index on

    lower(btrim(name, E' \\t\\n\\r\\f\\v'))

but PostgreSQL escape strings have no ``\\v`` sequence — any character after a
backslash that is not listed in Table 4.1 of the SQL syntax chapter is taken
literally. The trim set was therefore *space, tab, newline, carriage return,
form feed and the letter ``v``*, which both let a real vertical tab (0x0B) slip
through and made ``Acme`` / ``Acmev`` collide on the unique index.

Revision 141 was meant to repair it but only rebuilt when the stored definition
lacked an ``E'`` literal, which it never does, so it never ran. This revision
rebuilds whenever the definition does not mention ``chr(11)``, which also
repairs databases where 141 already ran with the faulty expression.

Safety: names that the faulty index tolerated as distinct (they differ only by a
vertical tab) would now collide. Those groups are reported and the existing
index is kept rather than failing the deployment; de-duplicate and re-run.

Revision ID: 142_qr_product_name_index_vertical_tab
Revises: 141_qr_product_name_index_whitespace
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_index, has_table

revision: str = "142_qr_product_name_index_vertical_tab"
down_revision: str | Sequence[str] | None = "141_qr_product_name_index_whitespace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_qr_products_org_name_ci"

# Vertical tab is spelled with ``chr(11)`` because E'\v' is a literal 'v'.
_TRIM_WHITESPACE = "btrim(name, E' \\t\\n\\r\\f' || chr(11))"
_NAME_EXPRESSION = f"lower({_TRIM_WHITESPACE})"

# Expression left behind by 140/141; restored by ``downgrade()`` for symmetry.
_LEGACY_TRIM_WHITESPACE = "btrim(name, E' \\t\\n\\r\\f\\v')"
_LEGACY_NAME_EXPRESSION = f"lower({_LEGACY_TRIM_WHITESPACE})"

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
    if definition is not None and "chr(11)" in definition:
        # Already built from the corrected expression.
        return

    duplicates = op.get_bind().execute(_DUPLICATES_SQL).fetchall()
    if duplicates:
        preview = "; ".join(
            f"{row[0]} / '{row[1]}' x{row[2]}" for row in duplicates[:10]
        )
        print(
            f"WARNING: keeping the current '{INDEX_NAME}' index — "
            f"{len(duplicates)} name group(s) collide once a vertical tab is "
            f"trimmed correctly: {preview}. De-duplicate, then re-run this "
            "revision."
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
    """Restore the expression 140/141 left behind (kept for symmetry only)."""
    if not has_table("qr_products"):
        return
    if has_index("qr_products", INDEX_NAME):
        op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        f"{INDEX_NAME} ON qr_products (organization_id, {_LEGACY_NAME_EXPRESSION}) "
        "WHERE deleted_at IS NULL AND name IS NOT NULL "
        f"AND {_LEGACY_TRIM_WHITESPACE} <> ''"
    )
