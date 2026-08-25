"""Drop Qseal-only sync columns from items (Phase 4).

Revision ID: 083_drop_item_qseal_sync_columns
Revises: 082_item_product_sku_link

Removes the columns that were mirrored from QRProduct via the (now-deleted)
``product_item_sync_service``. ``brand_id`` and ``gtin`` are kept (WMS-relevant).
"""

from collections.abc import Sequence

from alembic import op

from app.alembic_guards import has_column

revision: str = "083_drop_item_qseal_sync_columns"
down_revision: str | Sequence[str] | None = "082_item_product_sku_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DROPPED_COLUMNS = [
    "industry",
    "landing_page",
    "warranty_period_months",
    "qr_type",
    "activation_method",
    "sr_number_type",
]


def upgrade() -> None:
    for col in DROPPED_COLUMNS:
        if has_column("items", col):
            op.drop_column("items", col)


def downgrade() -> None:
    # Columns are dropped irreversibly here (data was a stale mirror). To
    # restore, re-run migration 069_sync_item_product_add_missing_columns.
    pass
