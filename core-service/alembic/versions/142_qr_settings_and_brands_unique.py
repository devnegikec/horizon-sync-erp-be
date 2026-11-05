"""Enforce case-insensitive organization-scoped uniqueness for QSeal lookups.

Channels, destinations, shelf-life values, brand names, and brand short codes
must not be duplicated within an organization. Soft-deleted rows do not reserve
their values. The settings index replaces the serial-prefix-only index created
by revision 141 so all setting types share one database guarantee.

Existing duplicates are repaired rather than fatal: references are moved to the
oldest row of each group and the duplicates are soft-deleted. Migrations run on
every container start, so a data-quality problem must never take the API down.

Revision ID: 142_qr_settings_and_brands_unique
Revises: 141_qr_serial_prefix_unique
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_index, has_table

revision: str = "142_qr_settings_and_brands_unique"
down_revision: str | Sequence[str] | None = "141_qr_serial_prefix_unique"
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
    """Keep the oldest row per key and move every reference onto it.

    Rows in a duplicate group hold the same value by definition, so retiring
    the extra ones is lossless: the keeper keeps the value, references are
    repointed first, and the duplicates are soft-deleted.
    """
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


def _report(revision_step: str, what: str, retired: int) -> None:
    if retired:
        print(
            f"{revision_step}: retired {retired} duplicate {what} row(s) after "
            "moving references to the oldest row."
        )


def upgrade() -> None:
    # Migrations run on every container start, so a data-quality problem must
    # never abort startup: duplicates are repaired in place and any unexpected
    # error is reported while the index is deferred to a later deploy.
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
            _report("142_qr_settings_and_brands_unique", "QR product setting", retired)
            # Create the wider index before dropping the narrower one so a
            # failure never leaves the table without a guard.
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
                f"WARNING: 142_qr_settings_and_brands_unique skipped "
                f"'{SETTINGS_INDEX}' ({type(exc).__name__}: {exc}). Setting "
                "uniqueness stays enforced by the service layer."
            )

    if has_table("brands"):
        try:
            retired = _repair_duplicates(
                "brands",
                BRAND_NAME_KEY,
                BRAND_NAME_WHERE,
                [("qr_products", "brand_id")],
            )
            _report("142_qr_settings_and_brands_unique", "brand-name", retired)

            retired = _repair_duplicates("brands", BRAND_CODE_KEY, BRAND_CODE_WHERE, [])
            _report("142_qr_settings_and_brands_unique", "brand-short-code", retired)

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
                "WARNING: 142_qr_settings_and_brands_unique skipped the brand "
                f"unique indexes ({type(exc).__name__}: {exc}). Brand "
                "uniqueness stays enforced by the service layer."
            )


def downgrade() -> None:
    if has_table("brands"):
        if has_index("brands", BRAND_SHORT_CODE_INDEX):
            op.drop_index(BRAND_SHORT_CODE_INDEX, table_name="brands")
        if has_index("brands", BRAND_NAME_INDEX):
            op.drop_index(BRAND_NAME_INDEX, table_name="brands")

    if has_table("qr_product_settings"):
        if has_index("qr_product_settings", SETTINGS_INDEX):
            op.drop_index(SETTINGS_INDEX, table_name="qr_product_settings")
        if not has_index("qr_product_settings", SERIAL_PREFIX_INDEX):
            op.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                f"{SERIAL_PREFIX_INDEX} ON qr_product_settings "
                "(organization_id, lower(btrim(value))) "
                "WHERE setting_type = 'serial_prefix' "
                "AND deleted_at IS NULL AND value IS NOT NULL "
                "AND btrim(value) <> ''"
            )
