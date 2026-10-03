"""Link Item ↔ ProductSKU (Phase 3, Option A — link, don't unify).

Revision ID: 082_item_product_sku_link
Revises: 081_products

Adds ``items.product_sku_id`` (FK -> product_skus.id) and back-fills it by
matching ``items.sku`` to ``product_skus.sku_code`` within the same
organization. ``items.variant_of`` / ``variant_attributes`` are kept (not
dropped) — deprecation is gradual.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.alembic_guards import has_column, has_constraint, has_index

revision: str = "082_item_product_sku_link"
down_revision: str | Sequence[str] | None = "081_products"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not has_column("items", "product_sku_id"):
        op.add_column(
            "items",
            sa.Column("product_sku_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
    if not has_index("items", "ix_items_product_sku_id"):
        op.create_index("ix_items_product_sku_id", "items", ["product_sku_id"])

    # Back-fill: link items to the matching ProductSKU by sku == sku_code.
    op.execute("""
        UPDATE items i SET product_sku_id = ps.id
        FROM product_skus ps
        WHERE i.organization_id = ps.organization_id
          AND i.sku IS NOT NULL
          AND i.sku = ps.sku_code
          AND ps.deleted_at IS NULL
          AND i.product_sku_id IS NULL
    """)

    if not has_constraint("items", "fk_items_product_sku_id_product_skus"):
        op.create_foreign_key(
            "fk_items_product_sku_id_product_skus",
            "items", "product_skus", ["product_sku_id"], ["id"],
        )


def downgrade() -> None:
    if has_constraint("items", "fk_items_product_sku_id_product_skus"):
        op.drop_constraint("fk_items_product_sku_id_product_skus", "items", type_="foreignkey")
    if has_column("items", "product_sku_id"):
        op.drop_index("ix_items_product_sku_id", table_name="items")
        op.drop_column("items", "product_sku_id")
