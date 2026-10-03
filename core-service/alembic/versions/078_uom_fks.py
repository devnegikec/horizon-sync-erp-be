"""Add UOM FK columns and back-fill from legacy string caches.

Revision ID: 078_uom_fks
Revises: 077_merge_phase0_heads

- ``uoms`` gains ``uom_type`` and ``precision``.
- ``items`` gains ``base_uom_id`` (FK -> uoms.id), back-filled from ``items.uom``.
- ``uom_conversions`` gains ``from_uom_id`` / ``to_uom_id`` (FK -> uoms.id),
  back-filled from the string columns, and ``item_id`` becomes nullable to allow
  global (item-independent) conversions.
- ``item_groups`` gains ``default_uom_id`` (FK -> uoms.id), back-filled from
  ``default_uom``.

Legacy string columns are retained as caches and are not dropped here.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.alembic_guards import has_column, has_constraint, has_index

revision: str = "078_uom_fks"
down_revision: str | Sequence[str] | None = "077_merge_phase0_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_column(table: str, column: str, col: sa.Column) -> None:
    if not has_column(table, column):
        op.add_column(table, col)


def _add_index(table: str, index: str, columns: list[str]) -> None:
    if not has_index(table, index):
        op.create_index(index, table, columns)


def _add_fk(name: str, source: str, referent: str, local_cols: list[str], remote_cols: list[str]) -> None:
    if not has_constraint(source, name):
        op.create_foreign_key(name, source, referent, local_cols, remote_cols)


def upgrade() -> None:
    # 1) uoms.uom_type + precision
    _add_column("uoms", "uom_type", sa.Column("uom_type", sa.String(20), nullable=True))
    _add_column("uoms", "precision", sa.Column("precision", sa.Integer(), nullable=False, server_default="0"))

    # 2) items.base_uom_id
    _add_column("items", "base_uom_id", sa.Column("base_uom_id", postgresql.UUID(as_uuid=True), nullable=True))
    _add_index("items", "ix_items_base_uom_id", ["base_uom_id"])

    # 3) uom_conversions — nullable item_id + FK columns
    op.alter_column(
        "uom_conversions", "item_id",
        existing_type=postgresql.UUID(as_uuid=True), nullable=True,
    )
    _add_column("uom_conversions", "from_uom_id", sa.Column("from_uom_id", postgresql.UUID(as_uuid=True), nullable=True))
    _add_column("uom_conversions", "to_uom_id", sa.Column("to_uom_id", postgresql.UUID(as_uuid=True), nullable=True))
    _add_index("uom_conversions", "ix_uom_conversions_from_uom_id", ["from_uom_id"])
    _add_index("uom_conversions", "ix_uom_conversions_to_uom_id", ["to_uom_id"])

    # 4) item_groups.default_uom_id
    _add_column("item_groups", "default_uom_id", sa.Column("default_uom_id", postgresql.UUID(as_uuid=True), nullable=True))

    # ── Back-fills ─────────────────────────────────────────────────────────
    # items.base_uom_id — match abbreviation first, then name.
    op.execute("""
        UPDATE items i SET base_uom_id = u.id
        FROM uoms u
        WHERE i.organization_id = u.organization_id
          AND upper(coalesce(i.uom, '')) = upper(u.abbreviation)
          AND u.deleted_at IS NULL
          AND i.base_uom_id IS NULL
    """)
    op.execute("""
        UPDATE items i SET base_uom_id = u.id
        FROM uoms u
        WHERE i.organization_id = u.organization_id
          AND upper(coalesce(i.uom, '')) = upper(u.name)
          AND u.deleted_at IS NULL
          AND i.base_uom_id IS NULL
    """)

    # uom_conversions from/to_uom_id — abbreviation then name.
    for direction in ("from", "to"):
        op.execute(
            f"""
            UPDATE uom_conversions uc SET {direction}_uom_id = u.id
            FROM uoms u
            WHERE uc.organization_id = u.organization_id
              AND upper(uc.{direction}_uom) = upper(u.abbreviation)
              AND u.deleted_at IS NULL
              AND uc.{direction}_uom_id IS NULL
            """
        )
        op.execute(
            f"""
            UPDATE uom_conversions uc SET {direction}_uom_id = u.id
            FROM uoms u
            WHERE uc.organization_id = u.organization_id
              AND upper(uc.{direction}_uom) = upper(u.name)
              AND u.deleted_at IS NULL
              AND uc.{direction}_uom_id IS NULL
            """
        )

    # item_groups.default_uom_id — abbreviation then name.
    # The legacy string cache column does not exist on fresh databases (the
    # model references default_uom_id directly), so guard the backfill.
    if has_column("item_groups", "default_uom"):
        op.execute("""
            UPDATE item_groups g SET default_uom_id = u.id
            FROM uoms u
            WHERE g.organization_id = u.organization_id
              AND upper(coalesce(g.default_uom, '')) = upper(u.abbreviation)
              AND u.deleted_at IS NULL
              AND g.default_uom_id IS NULL
        """)
        op.execute("""
            UPDATE item_groups g SET default_uom_id = u.id
            FROM uoms u
            WHERE g.organization_id = u.organization_id
              AND upper(coalesce(g.default_uom, '')) = upper(u.name)
              AND u.deleted_at IS NULL
              AND g.default_uom_id IS NULL
        """)

    # ── Foreign keys ────────────────────────────────────────────────────────
    _add_fk("fk_items_base_uom_id_uoms", "items", "uoms", ["base_uom_id"], ["id"])
    _add_fk("fk_uom_conversions_from_uom_id_uoms", "uom_conversions", "uoms", ["from_uom_id"], ["id"])
    _add_fk("fk_uom_conversions_to_uom_id_uoms", "uom_conversions", "uoms", ["to_uom_id"], ["id"])
    _add_fk("fk_item_groups_default_uom_id_uoms", "item_groups", "uoms", ["default_uom_id"], ["id"])


def downgrade() -> None:
    for name, source, cols in (
        ("fk_items_base_uom_id_uoms", "items", ["base_uom_id"]),
        ("fk_uom_conversions_from_uom_id_uoms", "uom_conversions", ["from_uom_id"]),
        ("fk_uom_conversions_to_uom_id_uoms", "uom_conversions", ["to_uom_id"]),
        ("fk_item_groups_default_uom_id_uoms", "item_groups", ["default_uom_id"]),
    ):
        if has_constraint(source, name):
            op.drop_constraint(name, source, type_="foreignkey")

    if has_column("items", "base_uom_id"):
        op.drop_index("ix_items_base_uom_id", table_name="items")
        op.drop_column("items", "base_uom_id")
    if has_column("uom_conversions", "from_uom_id"):
        op.drop_index("ix_uom_conversions_from_uom_id", table_name="uom_conversions")
        op.drop_column("uom_conversions", "from_uom_id")
    if has_column("uom_conversions", "to_uom_id"):
        op.drop_index("ix_uom_conversions_to_uom_id", table_name="uom_conversions")
        op.drop_column("uom_conversions", "to_uom_id")
    if has_column("item_groups", "default_uom_id"):
        op.drop_column("item_groups", "default_uom_id")
    if has_column("uoms", "uom_type"):
        op.drop_column("uoms", "uom_type")
    if has_column("uoms", "precision"):
        op.drop_column("uoms", "precision")

    op.alter_column(
        "uom_conversions", "item_id",
        existing_type=postgresql.UUID(as_uuid=True), nullable=False,
    )
