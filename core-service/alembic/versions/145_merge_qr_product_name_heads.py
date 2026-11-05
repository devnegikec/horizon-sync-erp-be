"""Merge the QR-product migration branches and settle the name index.

Two branches grew independently from ``140_qr_product_unique_name``:

* ``141_qr_product_name_index_whitespace`` → ``142_qr_product_name_index_vertical_tab``
  (dev) rebuild ``uq_qr_products_org_name_ci`` with a whitespace-aware trim;
* ``141_qr_serial_prefix_unique`` → ``142_qr_settings_and_brands_unique`` →
  ``143_brand_field_lengths`` → ``144_allow_duplicate_qr_product_names``
  (QSeal product management).

``144`` deliberately drops the unique product-name index because names are
descriptive labels, not identity keys (SKU remains the org-scoped key). The dev
branch, by contrast, *creates* that index, so without this merge revision the
final schema would depend on whichever branch alembic happened to walk last.

This revision is the single head: it runs after both branches and re-applies the
QSeal decision (no unique product-name index) so the outcome is deterministic.

Revision ID: 145_merge_qr_product_name_heads
Revises: 142_qr_product_name_index_vertical_tab, 144_allow_duplicate_qr_product_names
Create Date: 2026-11-04
"""

from collections.abc import Sequence

from alembic import op
from app.alembic_guards import has_index, has_table

revision: str = "145_merge_qr_product_name_heads"
down_revision: str | Sequence[str] | None = (
    "142_qr_product_name_index_vertical_tab",
    "144_allow_duplicate_qr_product_names",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NAME_INDEX = "uq_qr_products_org_name_ci"


def upgrade() -> None:
    # Final intent: duplicate active product names are allowed per organization.
    if has_table("qr_products") and has_index("qr_products", NAME_INDEX):
        op.execute(f"DROP INDEX IF EXISTS {NAME_INDEX}")


def downgrade() -> None:
    """A merge revision has no single downgrade path.

    Alembic cannot know which parent branch to unwind. Downgrade one branch
    explicitly, then re-run, e.g.
    ``alembic downgrade 142_qr_product_name_index_vertical_tab`` or
    ``alembic downgrade 144_allow_duplicate_qr_product_names``.
    """
    raise RuntimeError(
        "Cannot downgrade merge revision '145_merge_qr_product_name_heads'. "
        "Downgrade one of its parent branches explicitly first: "
        "'142_qr_product_name_index_vertical_tab' or "
        "'144_allow_duplicate_qr_product_names'."
    )
