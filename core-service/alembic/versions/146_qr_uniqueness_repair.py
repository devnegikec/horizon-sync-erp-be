"""Apply the QSeal uniqueness repair that 141/142 could not finish.

Revisions ``141_qr_serial_prefix_unique`` and ``142_qr_settings_and_brands_unique``
repaired duplicate rows and then created their unique indexes. On the first
deploy the repair statement was handed to ``Connection.execute`` as a plain
string (``ObjectNotExecutableError``); their defensive handler swallowed the
error, so the revisions were stamped without collapsing the duplicates or
creating the indexes.

This revision re-runs the same repair with properly bound ``sa.text`` statements
and creates the indexes. It is idempotent: every step checks existing state, so
it is a no-op on databases where 141/142 already did the work.

Revision ID: 146_qr_uniqueness_repair
Revises: 145_merge_qr_product_name_heads
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_index, has_table

revision: str = "146_qr_uniqueness_repair"
down_revision: str | Sequence[str] | None = "145_merge_qr_product_name_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SETTINGS_INDEX = "uq_qr_prod_settings_org_type_value_ci"
SERIAL_PREFIX_INDEX = "uq_qr_prod_settings_org_serial_prefix_ci"
BRAND_NAME_INDEX = "uq_brands_org_name_ci"
BRAND_SHORT_CODE_INDEX = "uq_brands_org_short_code_ci"

SETTINGS_KEY = "setting_type || '::' || lower(btrim(value))"
SETTINGS_WHERE = "deleted_at IS NULL AND value IS NOT NULL AND btrim(value) <> ''"
BRAND_NAME_KEY = "lower(btrim(name))"
BRAND_NAME_WHERE = "deleted_at IS NULL AND name IS NOT NULL AND btrim(name) <> ''"
BRAND_CODE_KEY = "lower(btrim(short_code))"
BRAND_CODE_WHERE = (
    "deleted_at IS NULL AND short_code IS NOT NULL AND btrim(short_code) <> ''"
)


def _repair_duplicates(
    table: str,
    key_expression: str,
    where: str,
    references: list[tuple[str, str]],
) -> int:
    """Keep the oldest row per key, repoint references, soft-delete the rest."""
    ranked = f"""
        SELECT id,
               first_value(id) OVER (
                   PARTITION BY organization_id, {key_expression}
                   ORDER BY created_at, id
               ) AS keeper_id
        FROM {table}
        WHERE {where}
    """

    for ref_table, ref_column in references:
        if not has_table(ref_table):
            continue
        op.execute(
            f"""
            WITH ranked AS ({ranked})
            UPDATE {ref_table} t
               SET {ref_column} = r.keeper_id
              FROM ranked r
             WHERE t.{ref_column} = r.id
               AND r.id <> r.keeper_id
            """
        )

    return (
        op.get_bind()
        .execute(
            sa.text(
                f"""
            WITH ranked AS ({ranked})
            UPDATE {table} x
               SET deleted_at = now()
              FROM ranked r
             WHERE x.id = r.id
               AND r.id <> r.keeper_id
            """
            )
        )
        .rowcount
        or 0
    )


def _report(what: str, retired: int) -> None:
    if retired:
        print(
            f"146_qr_uniqueness_repair: retired {retired} duplicate {what} "
            "row(s) after moving references to the oldest row."
        )


def upgrade() -> None:
    # Startup must never be blocked by data quality, but it also must not be
    # silently skipped: every branch below reports what it did.
    if has_table("qr_product_settings"):
        try:
            retired = _repair_duplicates(
                "qr_product_settings",
                SETTINGS_KEY,
                SETTINGS_WHERE,
                [
                    ("qr_products", "shelf_life_setting_id"),
                    ("qr_products", "serial_prefix_setting_id"),
                    ("qr_blocks", "channel_setting_id"),
                    ("qr_blocks", "destination_setting_id"),
                ],
            )
            _report("QR product setting", retired)
            if not has_index("qr_product_settings", SETTINGS_INDEX):
                op.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    f"{SETTINGS_INDEX} ON qr_product_settings "
                    "(organization_id, setting_type, lower(btrim(value))) "
                    "WHERE deleted_at IS NULL AND value IS NOT NULL "
                    "AND btrim(value) <> ''"
                )
            if has_index("qr_product_settings", SERIAL_PREFIX_INDEX):
                op.drop_index(SERIAL_PREFIX_INDEX, table_name="qr_product_settings")
        except Exception as exc:  # pragma: no cover - defensive
            print(
                "WARNING: 146_qr_uniqueness_repair skipped "
                f"'{SETTINGS_INDEX}' ({type(exc).__name__}: {exc})."
            )

    if has_table("brands"):
        try:
            retired = _repair_duplicates(
                "brands",
                BRAND_NAME_KEY,
                BRAND_NAME_WHERE,
                [("qr_products", "brand_id")],
            )
            _report("brand-name", retired)

            retired = _repair_duplicates("brands", BRAND_CODE_KEY, BRAND_CODE_WHERE, [])
            _report("brand-short-code", retired)

            if not has_index("brands", BRAND_NAME_INDEX):
                op.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    f"{BRAND_NAME_INDEX} ON brands "
                    "(organization_id, lower(btrim(name))) "
                    "WHERE deleted_at IS NULL AND name IS NOT NULL "
                    "AND btrim(name) <> ''"
                )
            if not has_index("brands", BRAND_SHORT_CODE_INDEX):
                op.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    f"{BRAND_SHORT_CODE_INDEX} ON brands "
                    "(organization_id, lower(btrim(short_code))) "
                    "WHERE deleted_at IS NULL AND short_code IS NOT NULL "
                    "AND btrim(short_code) <> ''"
                )
        except Exception as exc:  # pragma: no cover - defensive
            print(
                "WARNING: 146_qr_uniqueness_repair skipped the brand unique "
                f"indexes ({type(exc).__name__}: {exc})."
            )


def downgrade() -> None:
    """Drop the indexes 141/142 introduced; data repair is not reverted."""
    if has_table("brands"):
        if has_index("brands", BRAND_SHORT_CODE_INDEX):
            op.drop_index(BRAND_SHORT_CODE_INDEX, table_name="brands")
        if has_index("brands", BRAND_NAME_INDEX):
            op.drop_index(BRAND_NAME_INDEX, table_name="brands")

    if has_table("qr_product_settings") and has_index(
        "qr_product_settings", SETTINGS_INDEX
    ):
        op.drop_index(SETTINGS_INDEX, table_name="qr_product_settings")
