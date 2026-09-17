"""Add QSeal cascade tracking tables.

Revision ID: 067_add_qseal_cascade_tables
Revises: 066_link_asn_to_scan_sessions_and_receiving_slips
Create Date: 2026-08-12
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_index, has_table

revision: str = "067_add_qseal_cascade_tables"
down_revision: Union[str, None] = (
    "066_link_asn_to_scan_sessions_and_receiving_slips"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tracks are the parent/master-pack nodes and must exist before parameters
    # can reference them.
    if not has_table("qseal_tracks"):
        op.create_table(
            "qseal_tracks",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "organization_id", postgresql.UUID(as_uuid=True), nullable=False
            ),
            sa.Column("qseal_type", sa.String(25), nullable=True),
            sa.Column("name", sa.String(20), nullable=True),
            sa.Column("capacity", sa.Integer(), nullable=True),
            sa.Column("serial_number", sa.String(10), nullable=True),
            sa.Column("qseal_code_link", sa.Text(), nullable=True),
            sa.Column(
                "app_cascade_map",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "parent_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("qseal_tracks.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "parent_app_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("qseal_tracks.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    if not has_index("qseal_tracks", "ix_qseal_tracks_organization_id"):
        op.create_index(
            "ix_qseal_tracks_organization_id",
            "qseal_tracks",
            ["organization_id"],
        )

    if not has_table("qseal_parameters"):
        op.create_table(
            "qseal_parameters",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "organization_id", postgresql.UUID(as_uuid=True), nullable=False
            ),
            sa.Column(
                "product_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("qr_products.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "block_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("qr_blocks.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("serial_number", sa.String(75), nullable=True),
            sa.Column("manufacturing_date", sa.Date(), nullable=False),
            sa.Column("expiry_date", sa.Date(), nullable=False),
            sa.Column("manufacturing_unit", sa.String(100), nullable=False),
            sa.Column("dispatch_batch", sa.String(100), nullable=True),
            sa.Column("destination_market", sa.String(100), nullable=True),
            sa.Column("mrp", sa.Numeric(10, 2), nullable=True),
            sa.Column("currency", sa.String(10), nullable=True),
            sa.Column("batch_size", sa.Integer(), nullable=True),
            sa.Column(
                "qseal_settings",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "qseal_cascade",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "parent_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("qseal_tracks.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "parent_app_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("qseal_tracks.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("extra_data", postgresql.JSONB(), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    if not has_index("qseal_parameters", "ix_qseal_parameters_organization_id"):
        op.create_index(
            "ix_qseal_parameters_organization_id",
            "qseal_parameters",
            ["organization_id"],
        )


def downgrade() -> None:
    if has_table("qseal_parameters"):
        op.drop_table("qseal_parameters")
    if has_table("qseal_tracks"):
        op.drop_table("qseal_tracks")
