"""Limit QSeal brand name and short-code lengths.

A column is only narrowed when every stored value already fits: truncating a
brand name is destructive, and migrations run on every container start, so an
oversized row leaves the column unchanged and is reported in the deploy log
instead of aborting startup.

Revision ID: 143_brand_field_lengths
Revises: 142_qr_settings_and_brands_unique
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_table

revision: str = "143_brand_field_lengths"
down_revision: str | Sequence[str] | None = "142_qr_settings_and_brands_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _oversized_rows(column: str, maximum: int) -> list:
    return (
        op.get_bind()
        .execute(
            sa.text(
                f"""
            SELECT id, char_length({column}) AS value_length
            FROM brands
            WHERE {column} IS NOT NULL AND char_length({column}) > :maximum
            ORDER BY value_length DESC
            LIMIT 10
            """
            ),
            {"maximum": maximum},
        )
        .fetchall()
    )


def _narrow(column: str, maximum: int) -> None:
    """Shrink ``brands.<column>`` when every stored value already fits.

    Migrations run on every container start, so this must not abort startup.
    Truncating somebody's brand name is destructive, therefore an oversized row
    leaves the column at its current length and is reported instead.
    """
    rows = _oversized_rows(column, maximum)
    if rows:
        preview = "; ".join(f"{row[0]} ({row[1]} characters)" for row in rows)
        print(
            f"WARNING: 143_brand_field_lengths left brands.{column} unchanged — "
            f"{len(rows)}+ value(s) exceed {maximum} characters: {preview}. "
            "Shorten them and re-run this revision to apply the limit."
        )
        return

    op.alter_column(
        "brands",
        column,
        existing_type=sa.String(length=256),
        type_=sa.String(length=maximum),
    )


def upgrade() -> None:
    if not has_table("brands"):
        return

    _narrow("name", 20)
    _narrow("short_code", 8)


def downgrade() -> None:
    if not has_table("brands"):
        return

    op.alter_column(
        "brands",
        "short_code",
        existing_type=sa.String(length=8),
        type_=sa.String(length=256),
    )
    op.alter_column(
        "brands",
        "name",
        existing_type=sa.String(length=20),
        type_=sa.String(length=256),
    )
