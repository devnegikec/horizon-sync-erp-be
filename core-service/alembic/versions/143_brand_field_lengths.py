"""Limit QSeal brand name and short-code lengths.

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


def _raise_if_oversized(column: str, maximum: int) -> None:
    rows = (
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
    if rows:
        preview = "; ".join(f"{row[0]} ({row[1]} characters)" for row in rows)
        raise RuntimeError(
            f"Cannot limit brands.{column} to {maximum} characters. "
            f"Oversized rows: {preview}. Shorten these values, then re-run the migration."
        )


def upgrade() -> None:
    if not has_table("brands"):
        return

    _raise_if_oversized("name", 20)
    _raise_if_oversized("short_code", 8)

    op.alter_column(
        "brands",
        "name",
        existing_type=sa.String(length=256),
        type_=sa.String(length=20),
    )
    op.alter_column(
        "brands",
        "short_code",
        existing_type=sa.String(length=256),
        type_=sa.String(length=8),
    )


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
