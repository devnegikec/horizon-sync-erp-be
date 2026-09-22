"""Add QSeal context fields to scan events.

Revision ID: 115_add_qseal_scan_context
Revises: deac8f2179e0
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_constraint, has_index


revision: str = "115_add_qseal_scan_context"
down_revision: str | None = "deac8f2179e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = (
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("block_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("qseal_track_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("qseal_parameter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("batch", sa.String(50), nullable=True),
        sa.Column("qseal_type", sa.String(30), nullable=True),
    )
    for column in columns:
        if not has_column("qr_scan_events", column.name):
            op.add_column("qr_scan_events", column)

    foreign_keys = (
        ("fk_qr_scan_events_product_id", "product_id", "qr_products.id"),
        ("fk_qr_scan_events_block_id", "block_id", "qr_blocks.id"),
        ("fk_qr_scan_events_qseal_track_id", "qseal_track_id", "qseal_tracks.id"),
        (
            "fk_qr_scan_events_qseal_parameter_id",
            "qseal_parameter_id",
            "qseal_parameters.id",
        ),
    )
    for name, column, target in foreign_keys:
        if not has_constraint("qr_scan_events", name):
            op.create_foreign_key(
                name,
                "qr_scan_events",
                target.split(".")[0],
                [column],
                [target.split(".")[1]],
            )

    for name, column in (
        ("ix_qr_scan_events_product_id", "product_id"),
        ("ix_qr_scan_events_block_id", "block_id"),
        ("ix_qr_scan_events_qseal_track_id", "qseal_track_id"),
        ("ix_qr_scan_events_qseal_parameter_id", "qseal_parameter_id"),
        ("ix_qr_scan_events_batch", "batch"),
        ("ix_qr_scan_events_qseal_type", "qseal_type"),
    ):
        if not has_index("qr_scan_events", name):
            op.create_index(name, "qr_scan_events", [column])


def downgrade() -> None:
    for name in (
        "ix_qr_scan_events_qseal_type",
        "ix_qr_scan_events_batch",
        "ix_qr_scan_events_qseal_parameter_id",
        "ix_qr_scan_events_qseal_track_id",
        "ix_qr_scan_events_block_id",
        "ix_qr_scan_events_product_id",
    ):
        if has_index("qr_scan_events", name):
            op.drop_index(name, table_name="qr_scan_events")

    for name in (
        "fk_qr_scan_events_qseal_parameter_id",
        "fk_qr_scan_events_qseal_track_id",
        "fk_qr_scan_events_block_id",
        "fk_qr_scan_events_product_id",
    ):
        op.drop_constraint(name, "qr_scan_events", type_="foreignkey")

    for column in (
        "qseal_type",
        "batch",
        "qseal_parameter_id",
        "qseal_track_id",
        "block_id",
        "product_id",
    ):
        if has_column("qr_scan_events", column):
            op.drop_column("qr_scan_events", column)
