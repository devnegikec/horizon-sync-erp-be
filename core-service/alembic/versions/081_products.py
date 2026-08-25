"""Add shared products catalog core and link qr_products / items.

Revision ID: 081_products
Revises: 080_rename_stock_levels_product_id

- Creates the thin ``products`` catalog table.
- Adds ``qr_products.product_id`` (1:1) and ``items.product_id`` (1:N) FKs.
- Back-fills products from existing qr_products and standalone items.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.alembic_guards import has_column, has_constraint, has_index, has_table

revision: str = "081_products"
down_revision: str | Sequence[str] | None = "080_rename_stock_levels_product_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) products table
    if not has_table("products"):
        op.create_table(
            "products",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("sku", sa.String(100), nullable=True),
            sa.Column("gtin", sa.String(20), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("product_type", sa.String(20), nullable=True),
            sa.Column("images", postgresql.JSONB(), nullable=True),
            sa.Column("tags", postgresql.JSONB(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_products_organization_id", "products", ["organization_id"])
        op.create_index("ix_products_sku", "products", ["sku"])
        op.create_foreign_key(
            "fk_products_brand_id_brands", "products", "brands", ["brand_id"], ["id"]
        )

    # 2) qr_products.product_id (1:1)
    if not has_column("qr_products", "product_id"):
        op.add_column(
            "qr_products",
            sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
    if not has_index("qr_products", "ix_qr_products_product_id"):
        op.create_index("ix_qr_products_product_id", "qr_products", ["product_id"])

    # 3) items.product_id (1:N)
    if not has_column("items", "product_id"):
        op.add_column(
            "items",
            sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
    if not has_index("items", "ix_items_product_id"):
        op.create_index("ix_items_product_id", "items", ["product_id"])

    # 4) Back-fill products from qr_products (1:1 via temp mapping)
    op.execute("""
        CREATE TEMP TABLE _prod_map AS
        SELECT gen_random_uuid() AS new_id, qp.id AS qp_id, qp.organization_id,
               qp.name, qp.sku, qp.gtin, qp.brand_id
        FROM qr_products qp
        WHERE qp.deleted_at IS NULL
    """)
    op.execute("""
        INSERT INTO products (id, organization_id, name, sku, gtin, brand_id,
                              product_type, is_active, created_at, updated_at)
        SELECT new_id, organization_id, name, sku, gtin, brand_id,
               'qseal', true, now(), now()
        FROM _prod_map
    """)
    op.execute("""
        UPDATE qr_products qp SET product_id = m.new_id
        FROM _prod_map m WHERE qp.id = m.qp_id
    """)
    op.execute("DROP TABLE _prod_map")

    # 5) items with a linked qr_product inherit that product
    op.execute("""
        UPDATE items i SET product_id = qp.product_id
        FROM qr_products qp
        WHERE i.qr_product_id = qp.id AND i.product_id IS NULL
    """)

    # 6) Standalone items (no qr_product) get a 1:1 product
    op.execute("""
        CREATE TEMP TABLE _item_prod_map AS
        SELECT gen_random_uuid() AS new_id, i.id AS item_id, i.organization_id,
               i.item_name AS name, i.sku, i.gtin, i.brand_id
        FROM items i
        WHERE i.deleted_at IS NULL AND i.product_id IS NULL
    """)
    op.execute("""
        INSERT INTO products (id, organization_id, name, sku, gtin, brand_id,
                              product_type, is_active, created_at, updated_at)
        SELECT new_id, organization_id, name, sku, gtin, brand_id,
               'wms', true, now(), now()
        FROM _item_prod_map
    """)
    op.execute("""
        UPDATE items i SET product_id = m.new_id
        FROM _item_prod_map m WHERE i.id = m.item_id
    """)
    op.execute("DROP TABLE _item_prod_map")

    # 7) FK constraints
    if not has_constraint("qr_products", "fk_qr_products_product_id_products"):
        op.create_foreign_key(
            "fk_qr_products_product_id_products",
            "qr_products", "products", ["product_id"], ["id"],
        )
    if not has_constraint("items", "fk_items_product_id_products"):
        op.create_foreign_key(
            "fk_items_product_id_products",
            "items", "products", ["product_id"], ["id"],
        )


def downgrade() -> None:
    for name, source in (
        ("fk_items_product_id_products", "items"),
        ("fk_qr_products_product_id_products", "qr_products"),
    ):
        if has_constraint(source, name):
            op.drop_constraint(name, source, type_="foreignkey")
    if has_column("items", "product_id"):
        op.drop_index("ix_items_product_id", table_name="items")
        op.drop_column("items", "product_id")
    if has_column("qr_products", "product_id"):
        op.drop_index("ix_qr_products_product_id", table_name="qr_products")
        op.drop_column("qr_products", "product_id")
    if has_table("products"):
        op.drop_constraint("fk_products_brand_id_brands", "products", type_="foreignkey")
        op.drop_table("products")
