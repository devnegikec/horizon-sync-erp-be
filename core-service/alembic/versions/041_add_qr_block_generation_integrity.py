"""Add QR block generation contracts and active-row uniqueness.

Revision ID: 041_qr_block_integrity
Revises: 040_add_product_shelf_life
Create Date: 2026-07-29
"""

import sqlalchemy as sa

from alembic import op

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
    op.add_column(
        "qr_blocks",
        sa.Column(
            "qr_type",
            sa.String(length=30),
            nullable=False,
            server_default="dynamic",
        ),
    )
    op.add_column(
        "qr_blocks",
        sa.Column("starting_serial", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "qr_blocks",
        sa.Column(
            "generated_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "qr_blocks",
        sa.Column(
            "progress",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "qr_blocks",
        sa.Column("error_code", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "qr_blocks",
        sa.Column("error_message", sa.String(length=500), nullable=True),
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

    op.create_check_constraint(
        "ck_qr_blocks_qr_type",
        "qr_blocks",
        "qr_type IN "
        "('dynamic', 'static', 'dual', 'secure_code', 'one_time', "
        "'post_activation')",
    )
    op.create_check_constraint(
        "ck_qr_blocks_progress",
        "qr_blocks",
        "progress >= 0 AND progress <= 100",
    )

    _assert_no_active_duplicates()
    op.create_index(
        "uq_qr_blocks_org_batch_active",
        "qr_blocks",
        ["organization_id", sa.text("lower(batch)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
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
