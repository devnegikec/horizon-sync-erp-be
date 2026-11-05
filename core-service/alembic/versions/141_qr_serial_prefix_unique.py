"""Enforce case-insensitive unique active serial prefixes per organization.

Serial prefixes are normalized to uppercase by the service, while the index
also trims and lowercases values so legacy rows and direct database writes are
covered by the same uniqueness rule.

Existing duplicates are repaired rather than fatal: product references move to
the oldest row and the extra rows are soft-deleted (identical values, so
nothing is lost). Migrations run on every container start, so a data-quality
problem must never take the API down.

Revision ID: 141_qr_serial_prefix_unique
Revises: 140_qr_product_unique_name
Create Date: 2026-10-28
"""

from collections.abc import Sequence

from alembic import op
from app.alembic_guards import has_index, has_table

revision: str = "141_qr_serial_prefix_unique"
down_revision: str | Sequence[str] | None = "140_qr_product_unique_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_qr_prod_settings_org_serial_prefix_ci"

# Ranks every active serial prefix inside its (organization, normalised value)
# group and marks the oldest row as the keeper.
_RANKED_SQL = """
    SELECT id,
           first_value(id) OVER (
               PARTITION BY organization_id, lower(btrim(value))
               ORDER BY created_at, id
           ) AS keeper_id
    FROM qr_product_settings
    WHERE setting_type = 'serial_prefix'
      AND deleted_at IS NULL
      AND value IS NOT NULL
      AND btrim(value) <> ''
"""

#: Points products that use a duplicate at the keeper before it is retired.
_REPOINT_SQL = f"""
    WITH ranked AS ({_RANKED_SQL})
    UPDATE qr_products p
       SET serial_prefix_setting_id = r.keeper_id
      FROM ranked r
     WHERE p.serial_prefix_setting_id = r.id
       AND r.id <> r.keeper_id
"""

#: Soft-deletes every duplicate. The rows are identical by definition, so
#: nothing is lost — the keeper keeps the value and all references move to it.
_RETIRE_SQL = f"""
    WITH ranked AS ({_RANKED_SQL})
    UPDATE qr_product_settings s
       SET deleted_at = now()
      FROM ranked r
     WHERE s.id = r.id
       AND r.id <> r.keeper_id
"""


def _repair_duplicates() -> int:
    """Collapse duplicate serial prefixes onto the oldest row."""
    if has_table("qr_products"):
        op.execute(_REPOINT_SQL)
    return op.get_bind().execute(_RETIRE_SQL).rowcount or 0


def upgrade() -> None:
    if not has_table("qr_product_settings") or has_index(
        "qr_product_settings", INDEX_NAME
    ):
        return

    # Data quality must never keep the API down: migrations run on every
    # container start, so a hard failure here takes the whole service offline.
    # Duplicates are repaired in place; anything unexpected is reported and the
    # index is deferred to a later deploy.
    try:
        retired = _repair_duplicates()
        if retired:
            print(
                f"141_qr_serial_prefix_unique: retired {retired} duplicate "
                "serial-prefix setting(s) after moving product references to "
                "the oldest row."
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
    except Exception as exc:  # pragma: no cover - defensive
        print(
            f"WARNING: 141_qr_serial_prefix_unique skipped '{INDEX_NAME}' "
            f"({type(exc).__name__}: {exc}). Serial-prefix uniqueness stays "
            "enforced by the service layer; fix the data and re-run."
        )


def downgrade() -> None:
    if has_table("qr_product_settings") and has_index(
        "qr_product_settings", INDEX_NAME
    ):
        op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
