"""Add QR block generation contracts and active-row uniqueness.

Revision ID: 041_qr_block_integrity
Revises: 040_add_product_shelf_life
Create Date: 2026-07-29
"""

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_column, has_constraint, has_index, has_table

revision = "041_qr_block_integrity"
down_revision = "040_add_product_shelf_life"
branch_labels = None
depends_on = None


def _assert_no_active_duplicates() -> None:
    bind = op.get_bind()
    duplicate_batch = bind.execute(
        sa.text(
            """
            SELECT organization_id, lower(batch) AS normalized_batch
            FROM qr_blocks
            WHERE deleted_at IS NULL
            GROUP BY organization_id, lower(batch)
            HAVING count(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate_batch:
        raise RuntimeError(
            "Cannot add QR block batch uniqueness: active duplicate batches exist. "
            "Resolve duplicate (organization_id, case-insensitive batch) values "
            "before rerunning this migration."
        )

    duplicate_serial = bind.execute(
        sa.text(
            """
            SELECT organization_id, serial_number
            FROM product_items
            WHERE deleted_at IS NULL
            GROUP BY organization_id, serial_number
            HAVING count(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate_serial:
        raise RuntimeError(
            "Cannot add ProductItem serial uniqueness: active duplicate serial "
            "numbers exist. Resolve duplicate (organization_id, serial_number) "
            "values before rerunning this migration."
        )


def upgrade() -> None:
    if not has_table("qr_blocks"):
        return
    columns = (
        ("qr_type", sa.String(length=30), False, "dynamic"),
        ("starting_serial", sa.String(length=10), True, None),
        ("generated_count", sa.Integer(), False, "0"),
        ("progress", sa.Integer(), False, "0"),
        ("error_code", sa.String(length=50), True, None),
        ("error_message", sa.String(length=500), True, None),
    )
    for name, column_type, nullable, default in columns:
        if not has_column("qr_blocks", name):
            op.add_column(
                "qr_blocks",
                sa.Column(name, column_type, nullable=nullable, server_default=default),
            )

    op.execute(
        """
        UPDATE qr_blocks AS block
        SET qr_type = CASE upper(coalesce(product.qr_type, 'D'))
            WHEN 'S' THEN 'static'
            WHEN 'B' THEN 'dual'
            WHEN 'SC' THEN 'secure_code'
            WHEN 'O' THEN 'one_time'
            WHEN 'N' THEN 'post_activation'
            WHEN 'STATIC' THEN 'static'
            WHEN 'DUAL' THEN 'dual'
            WHEN 'SECURE_CODE' THEN 'secure_code'
            WHEN 'ONE_TIME' THEN 'one_time'
            WHEN 'POST_ACTIVATION' THEN 'post_activation'
            ELSE 'dynamic'
        END
        FROM qr_products AS product
        WHERE block.product_id = product.id
        """
    )

    if not has_constraint("qr_blocks", "ck_qr_blocks_qr_type"):
        op.create_check_constraint(
            "ck_qr_blocks_qr_type",
            "qr_blocks",
            "qr_type IN "
            "('dynamic', 'static', 'dual', 'secure_code', 'one_time', "
            "'post_activation')",
        )
    if not has_constraint("qr_blocks", "ck_qr_blocks_progress"):
        op.create_check_constraint(
            "ck_qr_blocks_progress",
            "qr_blocks",
            "progress >= 0 AND progress <= 100",
        )

    _assert_no_active_duplicates()
    if not has_index("qr_blocks", "uq_qr_blocks_org_batch_active"):
        op.create_index(
            "uq_qr_blocks_org_batch_active",
            "qr_blocks",
            ["organization_id", sa.text("lower(batch)")],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )
    if has_table("product_items") and not has_index("product_items", "uq_product_items_org_serial_active"):
        op.create_index(
            "uq_product_items_org_serial_active",
            "product_items",
            ["organization_id", "serial_number"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )


def downgrade() -> None:
    op.drop_index(
        "uq_product_items_org_serial_active",
        table_name="product_items",
    )
    op.drop_index(
        "uq_qr_blocks_org_batch_active",
        table_name="qr_blocks",
    )
    op.drop_constraint(
        "ck_qr_blocks_progress",
        "qr_blocks",
        type_="check",
    )
    op.drop_constraint(
        "ck_qr_blocks_qr_type",
        "qr_blocks",
        type_="check",
    )
    op.drop_column("qr_blocks", "error_message")
    op.drop_column("qr_blocks", "error_code")
    op.drop_column("qr_blocks", "progress")
    op.drop_column("qr_blocks", "generated_count")
    op.drop_column("qr_blocks", "starting_serial")
    op.drop_column("qr_blocks", "qr_type")
