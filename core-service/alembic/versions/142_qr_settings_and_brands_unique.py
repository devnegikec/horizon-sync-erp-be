"""Enforce case-insensitive organization-scoped uniqueness for QSeal lookups.

Channels, destinations, shelf-life values, brand names, and brand short codes
must not be duplicated within an organization. Soft-deleted rows do not reserve
their values. The settings index replaces the serial-prefix-only index created
by revision 141 so all setting types share one database guarantee.

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


def _duplicate_groups(table: str, expression: str, where: str):
    return (
        op.get_bind()
        .execute(
            sa.text(
                f"""
            SELECT organization_id, {expression} AS value_ci, count(*) AS n
            FROM {table}
            WHERE {where}
            GROUP BY 1, 2
            HAVING count(*) > 1
            ORDER BY 3 DESC, 2
            """
            )
        )
        .fetchall()
    )


def _raise_if_duplicates(
    table: str, expression: str, where: str, description: str
) -> None:
    duplicates = _duplicate_groups(table, expression, where)
    if not duplicates:
        return
    preview = "; ".join(f"{row[0]} / '{row[1]}' x{row[2]}" for row in duplicates[:10])
    raise RuntimeError(
        f"Cannot create unique {description} index: {len(duplicates)} "
        f"duplicate group(s) exist — {preview}. Resolve the duplicates, then "
        "re-run the migration."
    )


def upgrade() -> None:
    if has_table("qr_product_settings"):
        _raise_if_duplicates(
            "qr_product_settings",
            "setting_type || '::' || lower(btrim(value))",
            "deleted_at IS NULL AND value IS NOT NULL AND btrim(value) <> ''",
            "QR product setting",
        )

        if has_index("qr_product_settings", SERIAL_PREFIX_INDEX):
            op.drop_index(SERIAL_PREFIX_INDEX, table_name="qr_product_settings")
        if not has_index("qr_product_settings", SETTINGS_INDEX):
            op.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                f"{SETTINGS_INDEX} ON qr_product_settings "
                "(organization_id, setting_type, lower(btrim(value))) "
                "WHERE deleted_at IS NULL AND value IS NOT NULL "
                "AND btrim(value) <> ''"
            )

    if has_table("brands"):
        _raise_if_duplicates(
            "brands",
            "lower(btrim(name))",
            "deleted_at IS NULL AND name IS NOT NULL AND btrim(name) <> ''",
            "brand-name",
        )
        _raise_if_duplicates(
            "brands",
            "lower(btrim(short_code))",
            "deleted_at IS NULL AND short_code IS NOT NULL AND btrim(short_code) <> ''",
            "brand-short-code",
        )

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
