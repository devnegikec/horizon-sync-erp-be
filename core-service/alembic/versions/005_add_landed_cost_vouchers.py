"""Add landed cost vouchers table

Revision ID: 005_add_landed_cost_vouchers
Revises: 004_add_sourcing_flow_tables
Create Date: 2026-02-15 10:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "005_add_landed_cost_vouchers"
down_revision = "004_add_sourcing_flow_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create landed_cost_vouchers table
    op.create_table(
        "landed_cost_vouchers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voucher_no", sa.String(length=100), nullable=False),
        sa.Column("posting_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "submitted",
                "cancelled",
                name="documentstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_landed_cost_vouchers_organization_id"),
        "landed_cost_vouchers",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_landed_cost_vouchers_voucher_no"),
        "landed_cost_vouchers",
        ["voucher_no"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_landed_cost_vouchers_voucher_no"), table_name="landed_cost_vouchers"
    )
    op.drop_index(
        op.f("ix_landed_cost_vouchers_organization_id"),
        table_name="landed_cost_vouchers",
    )
    op.drop_table("landed_cost_vouchers")
