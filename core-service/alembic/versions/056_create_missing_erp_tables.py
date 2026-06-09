"""Create missing ERP tables (procurement / sourcing / fulfillment)

Revision ID: 056_create_missing_erp_tables
Revises: 055_fix_product_items_token_id_column
Create Date: 2026-06-09

Several SQLAlchemy models were used by services/repositories but were never
registered in ``app.models.__init__`` and had no migration creating their
tables. As a result the following tables were missing from freshly built
databases, causing 5xx errors on any endpoint that touched these features:

    communication_logs, delivery_notes, delivery_note_items,
    document_numbering_config, document_sequence_counter, item_prices,
    item_suppliers, landed_cost_vouchers, material_requests,
    material_request_lines, payments, purchase_orders, purchase_order_lines,
    purchase_receipts, purchase_receipt_items, put_away_rules,
    quality_inspections, quality_inspection_templates,
    quality_inspection_parameters, quality_inspection_readings,
    rfqs, rfq_lines, rfq_suppliers, supplier_quotes,
    status_transitions, stock_settings

The models are now registered in ``app.models.__init__``. This migration
materializes the missing tables (and any enum types they require) directly
from the model metadata. It is idempotent: ``checkfirst=True`` skips any
table/enum that already exists, so it is safe to run on databases where the
tables were already created out-of-band.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "056_create_missing_erp_tables"
down_revision = "055_fix_product_items_token_id_column"
branch_labels = None
depends_on = None


# Tables introduced by this migration (creation order is resolved automatically
# via metadata foreign-key dependency sorting).
MISSING_TABLES = [
    "communication_logs",
    "delivery_notes",
    "delivery_note_items",
    "document_numbering_config",
    "document_sequence_counter",
    "item_prices",
    "item_suppliers",
    "landed_cost_vouchers",
    "material_requests",
    "material_request_lines",
    "payments",
    "purchase_orders",
    "purchase_order_lines",
    "purchase_receipts",
    "purchase_receipt_items",
    "put_away_rules",
    "quality_inspection_templates",
    "quality_inspection_parameters",
    "quality_inspections",
    "quality_inspection_readings",
    "rfqs",
    "rfq_lines",
    "rfq_suppliers",
    "supplier_quotes",
    "status_transitions",
    "stock_settings",
]


def _target_tables():
    """Resolve the metadata Table objects for the missing tables."""
    import app.models  # noqa: F401  (registers all models on Base.metadata)
    from app.database import Base

    return [
        Base.metadata.tables[name]
        for name in MISSING_TABLES
        if name in Base.metadata.tables
    ]


def upgrade() -> None:
    bind = op.get_bind()
    tables = _target_tables()

    # Create only the tables that don't already exist (checkfirst=True), in
    # dependency order. Required enum types are created via checkfirst as well.
    from app.database import Base

    Base.metadata.create_all(bind=bind, tables=tables, checkfirst=True)


def downgrade() -> None:
    # Drop in reverse dependency order. CASCADE handles any dependent objects.
    for name in reversed(MISSING_TABLES):
        op.execute(f'DROP TABLE IF EXISTS "{name}" CASCADE')
