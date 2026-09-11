"""Add an index for fast tenant-scoped QR short-URL resolution."""

from alembic import op
from app.alembic_guards import has_index, has_table


revision = "077_add_product_item_token_lookup_index"
down_revision = "076_fix_legacy_qr_credit_ledger_column"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if has_table("product_items") and not has_index(
        "product_items", "ix_product_items_org_token_id"
    ):
        op.create_index(
            "ix_product_items_org_token_id",
            "product_items",
            ["organization_id", "token_id"],
            unique=False,
        )


def downgrade() -> None:
    if has_table("product_items") and has_index(
        "product_items", "ix_product_items_org_token_id"
    ):
        op.drop_index("ix_product_items_org_token_id", table_name="product_items")
