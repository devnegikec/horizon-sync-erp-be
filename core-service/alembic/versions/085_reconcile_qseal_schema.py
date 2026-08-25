"""Reconcile QSeal schema drift from the skipped 042-046 branch migrations.

The version table was previously stamped forward to `084` without executing
the QSeal branch (042_product_serial_config → 046_qr_credit_reservations),
leaving several ORM-model columns/tables missing from the live DB. This
migration re-applies those changes idempotently and also merges the two
current heads (076_add_vehicle_arrival_tables + 084_add_item_approval_columns)
into a single head.

Revision ID: 085_reconcile_qseal_schema
Revises: 076_add_vehicle_arrival_tables, 084_add_item_approval_columns
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.alembic_guards import has_column, has_constraint, has_index, has_table

revision: str = "085_reconcile_qseal_schema"
down_revision: str | Sequence[str] | None = (
    "076_add_vehicle_arrival_tables",
    "084_add_item_approval_columns",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 042_add_product_serial_configuration ────────────────────────────────
    if not has_column("qr_products", "serial_prefix_setting_id"):
        op.add_column(
            "qr_products",
            sa.Column(
                "serial_prefix_setting_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
    if not has_index("qr_products", "ix_qr_products_serial_prefix_setting_id"):
        op.create_index(
            "ix_qr_products_serial_prefix_setting_id",
            "qr_products",
            ["serial_prefix_setting_id"],
        )
    if not has_constraint(
        "qr_products", "fk_qr_products_serial_prefix_setting_id"
    ):
        op.create_foreign_key(
            "fk_qr_products_serial_prefix_setting_id",
            "qr_products",
            "qr_product_settings",
            ["serial_prefix_setting_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    # Normalize legacy Product sr_number_type values (idempotent).
    op.execute(
        """
        UPDATE qr_products
        SET sr_number_type = CASE lower(sr_number_type)
            WHEN 'random_8_alpha_numeric' THEN 'R8DAN'
            WHEN 'random_6_alpha_numeric' THEN 'R6DAN'
            WHEN 'random_4_alpha_numeric' THEN 'R4DAN'
            WHEN 'sequential' THEN 'S8DN'
            WHEN 'sequential_8_digit' THEN 'S8DN'
            WHEN 'sequential_10_digit' THEN 'S10DN'
            ELSE sr_number_type
        END
        WHERE sr_number_type IS NOT NULL
        """
    )

    # ── 043_add_qr_credit_management: Block setting references ──────────────
    for column_name in ("channel_setting_id", "destination_setting_id"):
        if not has_column("qr_blocks", column_name):
            op.add_column(
                "qr_blocks",
                sa.Column(
                    column_name,
                    postgresql.UUID(as_uuid=True),
                    nullable=True,
                ),
            )
        if not has_index("qr_blocks", f"ix_qr_blocks_{column_name}"):
            op.create_index(
                f"ix_qr_blocks_{column_name}",
                "qr_blocks",
                [column_name],
            )
        if not has_constraint("qr_blocks", f"fk_qr_blocks_{column_name}"):
            op.create_foreign_key(
                f"fk_qr_blocks_{column_name}",
                "qr_blocks",
                "qr_product_settings",
                [column_name],
                ["id"],
                ondelete="RESTRICT",
            )

    # ── 043_add_qr_credit_management: Ledger fields ─────────────────────────
    if has_column("qr_credit_ledger", "quantity_deducted") and not has_column(
        "qr_credit_ledger", "amount"
    ):
        op.alter_column(
            "qr_credit_ledger",
            "quantity_deducted",
            new_column_name="amount",
            existing_type=sa.Integer(),
        )
    if not has_column("qr_credit_ledger", "transaction_type"):
        op.add_column(
            "qr_credit_ledger",
            sa.Column("transaction_type", sa.String(length=30), nullable=True),
        )
    if not has_column("qr_credit_ledger", "reason"):
        op.add_column(
            "qr_credit_ledger",
            sa.Column("reason", sa.Text(), nullable=True),
        )
    if not has_column("qr_credit_ledger", "created_by"):
        op.add_column(
            "qr_credit_ledger",
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        )
    if not has_column("qr_credit_ledger", "reference_id"):
        op.add_column(
            "qr_credit_ledger",
            sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        )

    # Backfill only rows that haven't been converted yet (idempotent).
    op.execute(
        """
        UPDATE qr_credit_ledger
        SET transaction_type = 'block_consumption',
            amount = -abs(amount),
            reason = COALESCE(reason, 'QR Block generation')
        WHERE transaction_type IS NULL
        """
    )
    op.alter_column(
        "qr_credit_ledger",
        "transaction_type",
        existing_type=sa.String(length=30),
        nullable=False,
    )
    if not has_constraint(
        "qr_credit_ledger", "ck_qr_credit_ledger_amount_nonzero"
    ):
        op.create_check_constraint(
            "ck_qr_credit_ledger_amount_nonzero",
            "qr_credit_ledger",
            "amount <> 0",
        )
    if not has_index("qr_credit_ledger", "uq_qr_credit_ledger_org_reference"):
        op.create_index(
            "uq_qr_credit_ledger_org_reference",
            "qr_credit_ledger",
            ["organization_id", "reference_id"],
            unique=True,
            postgresql_where=sa.text("reference_id IS NOT NULL"),
        )
    if not has_index(
        "qr_credit_ledger", "uq_qr_credit_ledger_block_consumption"
    ):
        op.create_index(
            "uq_qr_credit_ledger_block_consumption",
            "qr_credit_ledger",
            ["block_id"],
            unique=True,
            postgresql_where=sa.text(
                "block_id IS NOT NULL AND transaction_type = 'block_consumption'"
            ),
        )

    # ── 044_add_qr_block_artifacts ──────────────────────────────────────────
    for col_name, col_type in (
        ("artifact_object_key", sa.Text()),
        ("artifact_size_bytes", sa.BigInteger()),
        ("artifact_checksum_sha256", sa.String(length=64)),
        ("artifact_generated_at", sa.DateTime(timezone=True)),
    ):
        if not has_column("qr_blocks", col_name):
            op.add_column("qr_blocks", sa.Column(col_name, col_type, nullable=True))

    # ── 046_add_qr_credit_reservations ──────────────────────────────────────
    if not has_column("qr_credit_balance", "reserved_credits"):
        op.add_column(
            "qr_credit_balance",
            sa.Column(
                "reserved_credits",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if not has_constraint(
        "qr_credit_balance", "ck_qr_credit_balance_reserved_nonnegative"
    ):
        op.create_check_constraint(
            "ck_qr_credit_balance_reserved_nonnegative",
            "qr_credit_balance",
            "reserved_credits >= 0",
        )

    if not has_table("qr_credit_reservations"):
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
    if not has_index(
        "qr_credit_reservations", "ix_qr_credit_reservations_organization_id"
    ):
        op.create_index(
            "ix_qr_credit_reservations_organization_id",
            "qr_credit_reservations",
            ["organization_id"],
        )
    if not has_index(
        "qr_credit_reservations", "ix_qr_credit_reservations_org_status"
    ):
        op.create_index(
            "ix_qr_credit_reservations_org_status",
            "qr_credit_reservations",
            ["organization_id", "status"],
        )


def downgrade() -> None:
    # Reverse in dependency order. Best-effort; guard each step.
    if has_table("qr_credit_reservations"):
        if has_index(
            "qr_credit_reservations", "ix_qr_credit_reservations_org_status"
        ):
            op.drop_index(
                "ix_qr_credit_reservations_org_status",
                table_name="qr_credit_reservations",
            )
        if has_index(
            "qr_credit_reservations", "ix_qr_credit_reservations_organization_id"
        ):
            op.drop_index(
                "ix_qr_credit_reservations_organization_id",
                table_name="qr_credit_reservations",
            )
        op.drop_table("qr_credit_reservations")

    if has_constraint(
        "qr_credit_balance", "ck_qr_credit_balance_reserved_nonnegative"
    ):
        op.drop_constraint(
            "ck_qr_credit_balance_reserved_nonnegative",
            "qr_credit_balance",
            type_="check",
        )
    if has_column("qr_credit_balance", "reserved_credits"):
        op.drop_column("qr_credit_balance", "reserved_credits")

    for col_name in (
        "artifact_generated_at",
        "artifact_checksum_sha256",
        "artifact_size_bytes",
        "artifact_object_key",
    ):
        if has_column("qr_blocks", col_name):
            op.drop_column("qr_blocks", col_name)

    if has_index("qr_credit_ledger", "uq_qr_credit_ledger_block_consumption"):
        op.drop_index(
            "uq_qr_credit_ledger_block_consumption",
            table_name="qr_credit_ledger",
        )
    if has_index("qr_credit_ledger", "uq_qr_credit_ledger_org_reference"):
        op.drop_index(
            "uq_qr_credit_ledger_org_reference",
            table_name="qr_credit_ledger",
        )
    if has_constraint("qr_credit_ledger", "ck_qr_credit_ledger_amount_nonzero"):
        op.drop_constraint(
            "ck_qr_credit_ledger_amount_nonzero",
            "qr_credit_ledger",
            type_="check",
        )
    for col_name in (
        "reference_id",
        "created_by",
        "reason",
        "transaction_type",
    ):
        if has_column("qr_credit_ledger", col_name):
            op.drop_column("qr_credit_ledger", col_name)
    if has_column("qr_credit_ledger", "amount") and not has_column(
        "qr_credit_ledger", "quantity_deducted"
    ):
        op.alter_column(
            "qr_credit_ledger",
            "amount",
            new_column_name="quantity_deducted",
            existing_type=sa.Integer(),
        )

    for column_name in ("destination_setting_id", "channel_setting_id"):
        if has_constraint("qr_blocks", f"fk_qr_blocks_{column_name}"):
            op.drop_constraint(
                f"fk_qr_blocks_{column_name}",
                "qr_blocks",
                type_="foreignkey",
            )
        if has_index("qr_blocks", f"ix_qr_blocks_{column_name}"):
            op.drop_index(
                f"ix_qr_blocks_{column_name}",
                table_name="qr_blocks",
            )
        if has_column("qr_blocks", column_name):
            op.drop_column("qr_blocks", column_name)

    if has_constraint("qr_products", "fk_qr_products_serial_prefix_setting_id"):
        op.drop_constraint(
            "fk_qr_products_serial_prefix_setting_id",
            "qr_products",
            type_="foreignkey",
        )
    if has_index("qr_products", "ix_qr_products_serial_prefix_setting_id"):
        op.drop_index(
            "ix_qr_products_serial_prefix_setting_id",
            table_name="qr_products",
        )
    if has_column("qr_products", "serial_prefix_setting_id"):
        op.drop_column("qr_products", "serial_prefix_setting_id")
