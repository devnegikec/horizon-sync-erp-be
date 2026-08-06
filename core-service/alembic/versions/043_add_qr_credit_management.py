"""Add SaaS QR-credit ledger fields and Block setting references.

Revision ID: 043_qr_credit_management
Revises: 042_product_serial_config
Create Date: 2026-07-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "043_qr_credit_management"
down_revision = "042_product_serial_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column_name in ("channel_setting_id", "destination_setting_id"):
        op.add_column(
            "qr_blocks",
            sa.Column(
                column_name,
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_index(
            f"ix_qr_blocks_{column_name}",
            "qr_blocks",
            [column_name],
        )
        op.create_foreign_key(
            f"fk_qr_blocks_{column_name}",
            "qr_blocks",
            "qr_product_settings",
            [column_name],
            ["id"],
            ondelete="RESTRICT",
        )

    op.alter_column(
        "qr_credit_ledger",
        "quantity_deducted",
        new_column_name="amount",
        existing_type=sa.Integer(),
    )
    op.add_column(
        "qr_credit_ledger",
        sa.Column("transaction_type", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "qr_credit_ledger",
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "qr_credit_ledger",
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "qr_credit_ledger",
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.execute(
        """
        UPDATE qr_credit_ledger
        SET transaction_type = 'block_consumption',
            amount = -abs(amount),
            reason = COALESCE(reason, 'QR Block generation')
        """
    )
    op.alter_column(
        "qr_credit_ledger",
        "transaction_type",
        existing_type=sa.String(length=30),
        nullable=False,
    )
    op.create_check_constraint(
        "ck_qr_credit_ledger_amount_nonzero",
        "qr_credit_ledger",
        "amount <> 0",
    )
    op.create_index(
        "uq_qr_credit_ledger_org_reference",
        "qr_credit_ledger",
        ["organization_id", "reference_id"],
        unique=True,
        postgresql_where=sa.text("reference_id IS NOT NULL"),
    )
    op.create_index(
        "uq_qr_credit_ledger_block_consumption",
        "qr_credit_ledger",
        ["block_id"],
        unique=True,
        postgresql_where=sa.text(
            "block_id IS NOT NULL AND transaction_type = 'block_consumption'"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_qr_credit_ledger_block_consumption",
        table_name="qr_credit_ledger",
    )
    op.drop_index(
        "uq_qr_credit_ledger_org_reference",
        table_name="qr_credit_ledger",
    )
    op.drop_constraint(
        "ck_qr_credit_ledger_amount_nonzero",
        "qr_credit_ledger",
        type_="check",
    )
    op.execute("UPDATE qr_credit_ledger SET amount = abs(amount)")
    op.drop_column("qr_credit_ledger", "reference_id")
    op.drop_column("qr_credit_ledger", "created_by")
    op.drop_column("qr_credit_ledger", "reason")
    op.drop_column("qr_credit_ledger", "transaction_type")
    op.alter_column(
        "qr_credit_ledger",
        "amount",
        new_column_name="quantity_deducted",
        existing_type=sa.Integer(),
    )

    for column_name in ("destination_setting_id", "channel_setting_id"):
        op.drop_constraint(
            f"fk_qr_blocks_{column_name}",
            "qr_blocks",
            type_="foreignkey",
        )
        op.drop_index(
            f"ix_qr_blocks_{column_name}",
            table_name="qr_blocks",
        )
        op.drop_column("qr_blocks", column_name)
