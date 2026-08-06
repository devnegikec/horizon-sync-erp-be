"""Add durable QR generation credit reservations.

Revision ID: 046_qr_credit_reservations
Revises: 045_expand_item_token_id
Create Date: 2026-08-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "046_qr_credit_reservations"
down_revision = "045_expand_item_token_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "qr_credit_balance",
        sa.Column(
            "reserved_credits",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_check_constraint(
        "ck_qr_credit_balance_reserved_nonnegative",
        "qr_credit_balance",
        "reserved_credits >= 0",
    )

    op.create_table(
        "qr_credit_reservations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "block_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="reserved",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_qr_credit_reservations_quantity",
        ),
        sa.CheckConstraint(
            "status IN ('reserved', 'consumed', 'released')",
            name="ck_qr_credit_reservations_status",
        ),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["qr_blocks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "block_id",
            name="uq_qr_credit_reservations_block",
        ),
    )
    op.create_index(
        "ix_qr_credit_reservations_organization_id",
        "qr_credit_reservations",
        ["organization_id"],
    )
    op.create_index(
        "ix_qr_credit_reservations_org_status",
        "qr_credit_reservations",
        ["organization_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_qr_credit_reservations_org_status",
        table_name="qr_credit_reservations",
    )
    op.drop_index(
        "ix_qr_credit_reservations_organization_id",
        table_name="qr_credit_reservations",
    )
    op.drop_table("qr_credit_reservations")
    op.drop_constraint(
        "ck_qr_credit_balance_reserved_nonnegative",
        "qr_credit_balance",
        type_="check",
    )
    op.drop_column("qr_credit_balance", "reserved_credits")
